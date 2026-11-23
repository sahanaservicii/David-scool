package ru.homeguard.agent;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.os.BatteryManager;
import android.os.Build;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.IBinder;
import android.os.PowerManager;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.HashMap;
import java.util.Map;

/**
 * Foreground sync loop: pushes device state to the parent console, pulls policy and commands.
 * Nothing is executed without a valid HMAC signature from the console.
 */
public class SyncService extends Service {

    public static final String ACTION_SOS = "ru.homeguard.SOS";
    private static final String CH_ID = "hg_agent_sync";
    private static final int NOTIF_ID = 1001;
    private static final int CHANNEL_ALERT = 1002;

    private HandlerThread thread;
    private Handler handler;
    private volatile boolean running;
    private volatile boolean pending;
    private volatile long nextDelay = 60_000L;
    private android.net.ConnectivityManager.NetworkCallback netCallback;
    private volatile String lastResult = "не подключались";

    public static String lastResult(Context c) {
        return Store.get(c, "last_sync_result", "ещё не было");
    }

    public static void start(Context c) {
        try {
            AgentLog.i("svc", "start requested");
            Intent i = new Intent(c, SyncService.class);
            if (Build.VERSION.SDK_INT >= 26) c.startForegroundService(i);
            else c.startService(i);
        } catch (Exception e) {
            AgentLog.e("svc", "start failed: " + e.getClass().getSimpleName() + ": " + e.getMessage());
        }
    }

    public static void sos(Context c) {
        Event.push(c, "sos", "ребёнок нажал SOS");
        start(c);
    }

    @Override
    public void onCreate() {
        super.onCreate();
        createChannels();
        startForeground(NOTIF_ID, notification("HomeGuard: запуск…"));
        thread = new HandlerThread("hg-sync");
        thread.start();
        handler = new Handler(thread.getLooper());
        watchNetwork();
    }

    /**
     * Wi-Fi <-> mobile data <-> VPN switches must not cost a whole backoff period:
     * reset the delay and sync immediately. Unsent events stay queued.
     */
    private void watchNetwork() {
        try {
            android.net.ConnectivityManager cm =
                    (android.net.ConnectivityManager) getSystemService(CONNECTIVITY_SERVICE);
            if (cm == null) return;
            netCallback = new android.net.ConnectivityManager.NetworkCallback() {
                @Override public void onAvailable(android.net.Network n) { wake(); }
                @Override public void onLost(android.net.Network n) { wake(); }
                @Override public void onCapabilitiesChanged(android.net.Network n,
                        android.net.NetworkCapabilities caps) { wake(); }
            };
            cm.registerDefaultNetworkCallback(netCallback);
        } catch (Exception ignored) {}
    }

    private void wake() {
        final Handler h = handler;
        if (h == null || !running) return;
        h.post(new Runnable() {
            @Override
            public void run() {
                if (!pending) return;          // sync already in progress
                h.removeCallbacks(loop);
                nextDelay = 1_000L;
                h.post(loop);
            }
        });
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && ACTION_SOS.equals(intent.getAction())) {
            Event.push(this, "sos", "ребёнок нажал SOS");
            nextDelay = 1_000L;
        }
        if (!running) {
            running = true;
            Scheduler.start(this);
            handler.post(loop);
        }
        return START_STICKY;
    }

    private final Runnable loop = new Runnable() {
        @Override
        public void run() {
            long delay = 60_000L;
            pending = false;
            try {
                syncOnce();
                delay = 60_000L;
                if (!isHomeNetwork()) delay = 120_000L;
            } catch (Exception e) {
                String msg = e.getMessage();
                if (msg == null || msg.isEmpty()) msg = e.getClass().getSimpleName();
                if (msg.length() > 120) msg = msg.substring(0, 120);
                Store.put(SyncService.this, "last_sync_result", "ошибка: " + msg);
                AgentLog.e("sync", "loop error: " + e.getClass().getSimpleName() + ": " + msg);
                delay = Math.min(nextDelay * 2, 240_000L);
            } finally {
                nextDelay = delay;
                updateNotification();
                handler.postDelayed(this, delay);
                pending = true;
            }
        }
    };

    private void syncOnce() throws Exception {
        final Context c = this;
        String secret = Store.secret(c);
        java.util.List<String> servers = Store.servers(c);
        if (servers.isEmpty() || secret == null) {
            lastResult = "нет привязки";
            AgentLog.w("sync", "no pairing: servers=" + servers.size() + " secret=" + (secret != null));
            Store.put(c, "last_sync_result", lastResult);
            return;
        }

        JSONObject state = buildState();
        String body = state.toString();
        AgentLog.i("sync", "start servers=" + servers + " events=" + (state.optJSONArray("events") == null ? 0 : state.optJSONArray("events").length()));

        // Try the endpoint that worked last time first, then the alternatives
        // (LAN at home, WireGuard outside).
        String active = Store.get(c, "server_active", null);
        if (active != null) {
            servers.remove(active);
            servers.add(0, active);
        }

        Http.Resp resp = null;
        String used = null;
        String lastError = "";
        for (String server : servers) {
            String ts = Protocol.nowTs();
            String nonce = Protocol.nonce();
            Map<String, String> headers = new HashMap<>();
            headers.put(Protocol.H_DEVICE, Store.deviceId(c));
            headers.put(Protocol.H_TS, ts);
            headers.put(Protocol.H_NONCE, nonce);
            headers.put(Protocol.H_SIG,
                    Protocol.sign(secret, "POST", Protocol.PATH_SYNC, ts, nonce, body));

            AgentLog.i("sync", "POST " + server + Protocol.PATH_SYNC);
            Http.Resp attempt;
            try {
                attempt = Http.post(server + Protocol.PATH_SYNC, headers, body, 6000, 12000);
            } catch (Exception ex) {
                String em = ex.getClass().getSimpleName() + ": " + ex.getMessage();
                AgentLog.e("sync", "exception " + server + " -> " + em);
                lastError = "EXC " + ex.getClass().getSimpleName();
                continue;
            }
            String bodyHint = attempt.body == null ? "" : attempt.body.replaceAll("[\r\n\t]+", " ").trim();
            if (bodyHint.length() > 120) bodyHint = bodyHint.substring(0, 120) + "…";
            AgentLog.i("sync", "resp " + server + " code=" + attempt.code + " body=" + bodyHint);
            if (attempt.ok()) {
                resp = attempt;
                used = server;
                break;
            }
            lastError = attempt.code == 401 ? "код неверный" : ("HTTP " + attempt.code);
            if (attempt.code == 401) break;
        }
        if (resp == null) {
            lastResult = "нет связи (" + lastError + ")";
            Store.put(c, "last_sync_result", lastResult);
            AgentLog.w("sync", "all servers failed: " + lastError);
            throw new IllegalStateException("no server: " + lastError);
        }
        Store.put(c, "server_active", used);
        if (!verifyResponse(secret, Protocol.PATH_SYNC, resp)) {
            lastResult = "ответ без подписи";
            Store.put(c, "last_sync_result", lastResult);
            AgentLog.e("sync", "bad response signature from " + used);
            throw new IllegalStateException("unverified response");
        }
        JSONObject r = new JSONObject(resp.body);
        // Console accepted the batch: drop exactly the events we sent.
        Event.commit(c, state.optJSONArray("events") == null ? 0 : state.optJSONArray("events").length());
        lastResult = "ok " + new java.text.SimpleDateFormat("HH:mm:ss", java.util.Locale.US)
                .format(new java.util.Date());
        Store.putLong(c, "last_sync", System.currentTimeMillis());
        Store.put(c, "last_sync_result", lastResult + " via " + used);
        AgentLog.i("sync", "ok via " + used + " policy=" + (r.optJSONObject("policy") != null ? r.optJSONObject("policy").optInt("v",-1) : -1));

        JSONObject policy = r.optJSONObject("policy");
        if (policy != null) {
            int incoming = policy.optInt("v", 0);
            if (incoming > Store.getInt(c, "policy_v", -1)) {
                JSONObject applied = Admin.apply(c, policy);
                Event.push(c, "policy", "v" + incoming + " " + applied.optBoolean("ok", false));
                Scheduler.tick(c);
            }
        }

        JSONArray cmds = r.optJSONArray("commands");
        if (cmds != null && cmds.length() > 0) {
            for (int i = 0; i < cmds.length(); i++) {
                JSONObject cmd = cmds.optJSONObject(i);
                if (cmd != null) handleCommand(cmd);
            }
        }
    }

    private void handleCommand(JSONObject cmd) {
        String id = cmd.optString("id", "");
        String type = cmd.optString("type", "");
        JSONObject args = cmd.optJSONObject("args");
        boolean ok = true;
        String result = "ok";
        try {
            switch (type) {
                case "lock":
                    LockState.lock(args != null ? args.optString("reason", "parent") : "parent");
                    CurfewActivity.show(this, LockState.reason);
                    Admin.lockNow(this);
                    Event.push(this, "lock", "parent");
                    result = "locked";
                    break;
                case "unlock":
                    LockState.unlock();
                    CurfewActivity.hide(this);
                    Store.putLong(this, "manual_override", System.currentTimeMillis() + 30 * 60_000L);
                    try {
                        Admin.dpm(this).setLockTaskPackages(Admin.cn(this),
                                new String[]{getPackageName()});
                    } catch (Exception ignored) {}
                    Event.push(this, "unlock", "parent");
                    result = "unlocked";
                    break;
                case "locate": {
                    JSONObject loc = LocationReporter.oneShot(this);
                    result = loc.toString();
                    break;
                }
                case "airplane": {
                    Admin.setAirplane(this, args != null && args.optBoolean("on", false));
                    result = "airplane";
                    break;
                }
                case "reboot":
                    Admin.dpm(this).reboot(null);
                    result = "rebooting";
                    break;
                case "wipe":
                    if (args != null && "WIPE".equals(args.optString("confirm", ""))) {
                        Admin.dpm(this).wipeData(0);
                        result = "wiping";
                    } else {
                        ok = false;
                        result = "confirm_required";
                    }
                    break;
                case "sync":
                    result = "now";
                    break;
                default:
                    ok = false;
                    result = "unknown_command";
            }
        } catch (Exception e) {
            ok = false;
            result = e.getClass().getSimpleName() + ": " + e.getMessage();
        }
        try {
            JSONObject ack = new JSONObject();
            ack.put("id", id);
            ack.put("ok", ok);
            ack.put("result", result);
            postAck(ack);
        } catch (Exception ignored) {}
    }

    private static final java.util.LinkedHashMap<String, Long> RESP_NONCES =
            new java.util.LinkedHashMap<String, Long>(64, 0.75f, true) {
                @Override
                protected boolean removeEldestEntry(java.util.Map.Entry<String, Long> e) {
                    return size() > 512;
                }
            };

    /**
     * The console signs every response with the same per-device secret:
     * {@code RESP|path|ts|nonce|sha256(body)}. Without a valid signature the
     * body is ignored, so a spoofed server cannot push policy or commands.
     */
    private boolean verifyResponse(String secret, String path, Http.Resp r) {
        String ts = r.header(Protocol.H_TS);
        String nonce = r.header(Protocol.H_NONCE);
        String sig = r.header(Protocol.H_SIG);
        if (ts == null || nonce == null || sig == null) return false;
        try {
            long t = Long.parseLong(ts);
            if (Math.abs(System.currentTimeMillis() / 1000L - t) > 300) return false;
        } catch (Exception e) {
            return false;
        }
        String expected = Protocol.sign(secret, Protocol.RESP, path, ts, nonce, r.body);
        if (!Protocol.constantTimeEquals(expected, sig)) return false;
        synchronized (RESP_NONCES) {
            if (RESP_NONCES.containsKey(nonce)) return false;
            long now = System.currentTimeMillis();
            RESP_NONCES.entrySet().removeIf(e -> now - e.getValue() > 600_000L);
            RESP_NONCES.put(nonce, now);
        }
        return true;
    }

    private void postAck(JSONObject ack) {
        String server = Store.get(this, "server_active", Store.serverUrl(this));
        String secret = Store.secret(this);
        if (server == null || secret == null) return;
        String body = ack.toString();
        String ts = Protocol.nowTs();
        String nonce = Protocol.nonce();
        Map<String, String> h = new HashMap<>();
        h.put(Protocol.H_DEVICE, Store.deviceId(this));
        h.put(Protocol.H_TS, ts);
        h.put(Protocol.H_NONCE, nonce);
        h.put(Protocol.H_SIG, Protocol.sign(secret, "POST", Protocol.PATH_ACK, ts, nonce, body));
        Http.post(server + Protocol.PATH_ACK, h, body, 6000, 8000);
    }

    private JSONObject buildState() throws Exception {
        JSONObject s = new JSONObject();
        s.put("agent", "1.0.0");
        s.put("device", Store.deviceId(this));
        s.put("name", Store.deviceName(this));
        s.put("sdk", Build.VERSION.SDK_INT);
        s.put("android", Build.VERSION.RELEASE);
        s.put("model", Build.MANUFACTURER + " " + Build.MODEL);
        s.put("do", Admin.isOwner(this));
        s.put("admin", Admin.isAdmin(this));
        s.put("battery", battery());
        s.put("charging", charging());
        s.put("screen", screenOn());
        s.put("fg", Usage.foregroundPackage(this));
        s.put("usage", Usage.usageJson(this, 12));
        s.put("today_min", Usage.totalMs(this) / 60000L);
        s.put("locked", LockState.locked);
        s.put("lock_reason", LockState.reason);
        s.put("policy_v", Store.getInt(this, "policy_v", -1));
        s.put("events", Event.peek(this));
        s.put("ts", System.currentTimeMillis() / 1000L);
        return s;
    }

    private int battery() {
        try {
            BatteryManager bm = (BatteryManager) getSystemService(BATTERY_SERVICE);
            return bm == null ? -1 : bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY);
        } catch (Exception e) {
            return -1;
        }
    }

    private boolean charging() {
        try {
            BatteryManager bm = (BatteryManager) getSystemService(BATTERY_SERVICE);
            return bm != null && bm.isCharging();
        } catch (Exception e) {
            return false;
        }
    }

    private boolean screenOn() {
        try {
            PowerManager pm = (PowerManager) getSystemService(POWER_SERVICE);
            return pm != null && pm.isInteractive();
        } catch (Exception e) {
            return false;
        }
    }

    /**
     * True when any Wi-Fi link is up. With always-on VPN the default network is the
     * tunnel, so the underlying transports have to be inspected as well.
     */
    private boolean isHomeNetwork() {
        try {
            android.net.ConnectivityManager cm =
                    (android.net.ConnectivityManager) getSystemService(CONNECTIVITY_SERVICE);
            if (cm == null) return false;
            for (android.net.Network n : cm.getAllNetworks()) {
                android.net.NetworkCapabilities caps = cm.getNetworkCapabilities(n);
                if (caps == null) continue;
                // getAllNetworks() still lists the Wi-Fi link while an always-on VPN
                // is the default network, so no extra unwrapping is needed.
                if (caps.hasTransport(android.net.NetworkCapabilities.TRANSPORT_WIFI)) return true;
            }
            return false;
        } catch (Exception e) {
            return false;
        }
    }

    private void createChannels() {
        NotificationManager nm = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
        if (nm == null) return;
        NotificationChannel ch = new NotificationChannel(CH_ID, "HomeGuard служба",
                NotificationManager.IMPORTANCE_MIN);
        ch.setShowBadge(false);
        nm.createNotificationChannel(ch);
        NotificationChannel alert = new NotificationChannel("hg_alerts", "HomeGuard тревоги",
                NotificationManager.IMPORTANCE_HIGH);
        nm.createNotificationChannel(alert);
    }

    private Notification notification(String text) {
        Intent open = new Intent(this, MainActivity.class);
        PendingIntent pi = PendingIntent.getActivity(this, 0, open,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        Notification.Builder b = Build.VERSION.SDK_INT >= 26
                ? new Notification.Builder(this, CH_ID) : new Notification.Builder(this);
        return b.setContentTitle("HomeGuard")
                .setContentText(text)
                .setSmallIcon(android.R.drawable.ic_lock_lock)
                .setOngoing(true)
                .setShowWhen(false)
                .setContentIntent(pi)
                .build();
    }

    private void updateNotification() {
        try {
            NotificationManager nm = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
            if (nm != null) nm.notify(NOTIF_ID, notification(lastResult));
        } catch (Exception ignored) {}
    }

    @Override
    public void onDestroy() {
        try {
            android.net.ConnectivityManager cm =
                    (android.net.ConnectivityManager) getSystemService(CONNECTIVITY_SERVICE);
            if (cm != null && netCallback != null) cm.unregisterNetworkCallback(netCallback);
        } catch (Exception ignored) {}

        running = false;
        if (handler != null) handler.removeCallbacksAndMessages(null);
        if (thread != null) thread.quitSafely();
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
