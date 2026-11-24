package ru.homeguard.console;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedInputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Embedded control server. Agents poll it; every request is HMAC-signed with the
 * per-device secret and protected against replay by timestamp + nonce. Responses
 * carry a signature too, so the agent never acts on an unsigned body.
 *
 * Exposure is limited to private peers and to a hard per-request deadline: the
 * server is meant for LAN/WireGuard only.
 */
public class ControlServer {

    public static final int PORT = 8787;
    private static final long SKEW_SEC = 300;
    private static final int MAX_BODY = 64 * 1024;
    private static final int MAX_HEADERS = 32;
    private static final int MAX_HEADER_BYTES = 16 * 1024;
    private static final int MAX_LINE = 4096;
    private static final long REQUEST_DEADLINE_MS = 15_000L;
    private static final int NONCE_TTL_MS = 600_000;
    private static final int NONCE_MAX = 10_000;

    private final Context ctx;
    private final Db db;
    private final ExecutorService pool = Executors.newFixedThreadPool(4);
    private final Map<String, Long> nonces = new ConcurrentHashMap<>();

    private ServerSocket socket;
    private Thread accept;
    private volatile boolean running;
    private volatile String lastError = "";

    public ControlServer(Context c) {
        this.ctx = c.getApplicationContext();
        this.db = Db.get(ctx);
        ServerLog.init(ctx);
    }

    public boolean isRunning() {
        return running;
    }

    public String lastError() {
        return lastError;
    }

    public synchronized void start() {
        if (running) return;
        try {
            socket = new ServerSocket();
            socket.setReuseAddress(true);
            socket.bind(new InetSocketAddress(PORT));
            running = true;
            ServerLog.i("сервер слушает :" + PORT);
            accept = new Thread(new Runnable() {
                @Override
                public void run() {
                    acceptLoop();
                }
            }, "hg-accept");
            accept.start();
        } catch (Exception e) {
            lastError = e.getClass().getSimpleName() + ": " + e.getMessage();
            ServerLog.e("старт не удался: " + lastError);
            running = false;
        }
    }

    public synchronized void stop() {
        running = false;
        ServerLog.w("сервер остановлен");
        try {
            if (socket != null) socket.close();
        } catch (Exception ignored) {}
        if (accept != null) accept.interrupt();
        pool.shutdownNow();
    }

    private void acceptLoop() {
        while (running) {
            try {
                final Socket s = socket.accept();
                if (!isPrivatePeer(s.getInetAddress())) {
                    String ip = s.getInetAddress() == null ? "?" : s.getInetAddress().getHostAddress();
                    ServerLog.w("отклонён не-LAN peer " + ip);
                    try { s.close(); } catch (Exception ignored) {}
                    continue;
                }
                s.setSoTimeout(8000);
                pool.submit(new Runnable() {
                    @Override
                    public void run() {
                        try {
                            handle(s);
                        } catch (Exception e) {
                            ServerLog.w("handle: " + e.getClass().getSimpleName());
                        } finally {
                            try { s.close(); } catch (Exception ignored) {}
                        }
                    }
                });
            } catch (Exception e) {
                if (running) {
                    lastError = String.valueOf(e.getMessage());
                    ServerLog.w("accept: " + e.getClass().getSimpleName());
                }
            }
        }
    }

    /** LAN, loopback, link-local and IPv6 ULA only — never a public address. */
    private static boolean isPrivatePeer(InetAddress a) {
        if (a == null) return false;
        if (a.isAnyLocalAddress() || a.isLoopbackAddress() || a.isLinkLocalAddress()
                || a.isSiteLocalAddress()) return true;
        byte[] b = a.getAddress();
        return b != null && b.length == 16 && (b[0] & 0xFE) == 0xFC;
    }

    private void handle(Socket s) throws Exception {
        long deadline = System.currentTimeMillis() + REQUEST_DEADLINE_MS;
        InputStream in = new BufferedInputStream(s.getInputStream());
        String reqLine = readLine(in, deadline);
        if (reqLine == null) return;
        String[] rl = reqLine.split(" ");
        if (rl.length < 2) return;
        String method = rl[0];
        String path = rl[1].split("\\?")[0];

        Map<String, String> h = new HashMap<>();
        int len = 0;
        int headerCount = 0;
        int headerBytes = 0;
        String line;
        while ((line = readLine(in, deadline)) != null && !line.isEmpty()) {
            headerCount++;
            headerBytes += line.length();
            if (headerCount > MAX_HEADERS || headerBytes > MAX_HEADER_BYTES) {
                respond(s, 431, "{\"ok\":false,\"error\":\"headers\"}", null, path);
                return;
            }
            int i = line.indexOf(':');
            if (i > 0) {
                String k = line.substring(0, i).trim().toLowerCase(java.util.Locale.ROOT);
                String v = line.substring(i + 1).trim();
                h.put(k, v);
                if (k.equals("content-length")) {
                    try {
                        len = Integer.parseInt(v);
                    } catch (Exception ignored) {}
                }
            }
        }
        if (len < 0 || len > MAX_BODY) {
            respond(s, 413, "{\"ok\":false}", null, path);
            return;
        }
        byte[] raw = readFully(in, len, deadline);
        String body = new String(raw, "UTF-8");

        String peer = s.getInetAddress() == null ? "?" : s.getInetAddress().getHostAddress();
        if ("GET".equals(method) && Protocol.PATH_PING.equals(path)) {
            ServerLog.i("ping от " + peer);
            JSONObject o = new JSONObject();
            o.put("ok", true);
            o.put("app", "homeguard-console");
            o.put("port", PORT);
            respond(s, 200, o.toString(), null, path);
            return;
        }

        if (!"POST".equals(method)) {
            ServerLog.w(peer + " " + method + " " + path + " -> 405");
            respond(s, 405, "{\"ok\":false,\"error\":\"method\"}", null, path);
            return;
        }

        String device = h.get(Protocol.H_DEVICE.toLowerCase());
        String ts = h.get(Protocol.H_TS.toLowerCase());
        String nonce = h.get(Protocol.H_NONCE.toLowerCase());
        String sig = h.get(Protocol.H_SIG.toLowerCase());

        Db.Device d = device == null ? null : db.device(device);
        if (!verify(d, ts, nonce, sig, path, body)) {
            ServerLog.w(peer + " " + path + " auth FAIL dev=" + (device == null ? "-" : device));
            respond(s, 401, "{\"ok\":false,\"error\":\"auth\"}", null, path);
            return;
        }

        if (Protocol.PATH_SYNC.equals(path)) {
            ServerLog.i(peer + " sync OK dev=" + device);
            DiagRelay.send(ctx, "sync_req", "dev=" + device + " from=" + peer, body);
            String respBody = onSync(device, body).toString();
            DiagRelay.send(ctx, "sync_resp", "dev=" + device + " to=" + peer, respBody);
            respond(s, 200, respBody, d, path);
        } else if (Protocol.PATH_ACK.equals(path)) {
            ServerLog.i(peer + " ack OK dev=" + device);
            DiagRelay.send(ctx, "ack_req", "dev=" + device + " from=" + peer, body);
            String respBody = onAck(device, body).toString();
            DiagRelay.send(ctx, "ack_resp", "dev=" + device + " to=" + peer, respBody);
            respond(s, 200, respBody, d, path);
        } else {
            ServerLog.w(peer + " " + path + " -> 404");
            respond(s, 404, "{\"ok\":false,\"error\":\"not_found\"}", null, path);
        }
    }

    private boolean verify(Db.Device d, String ts, String nonce, String sig, String path, String body) {
        if (d == null || d.secret == null || ts == null || nonce == null || sig == null) return false;
        try {
            long t = Long.parseLong(ts);
            if (Math.abs(System.currentTimeMillis() / 1000L - t) > SKEW_SEC) return false;
        } catch (Exception e) {
            return false;
        }
        if (nonce.length() < 16 || nonce.length() > 64) return false;
        for (int i = 0; i < nonce.length(); i++) {
            if (Character.digit(nonce.charAt(i), 16) < 0) return false;
        }

        String expected = Protocol.sign(d.secret, "POST", path, ts, nonce, body);
        if (!Protocol.constantTimeEquals(expected, sig)) return false;

        long now = System.currentTimeMillis();
        nonces.entrySet().removeIf(e -> now - e.getValue() > NONCE_TTL_MS);
        if (nonces.size() >= NONCE_MAX) return false;
        return nonces.putIfAbsent(nonce, now) == null;
    }

    private final List<String> toDelete = new ArrayList<>();

    private JSONObject onSync(String device, String body) {
        JSONObject resp = new JSONObject();
        try {
            JSONObject st = new JSONObject(body);
            db.saveState(device, body);
            JSONArray usage = st.optJSONArray("usage");
            if (usage != null) db.saveUsage(device, usage);

            JSONArray events = st.optJSONArray("events");
            if (events != null) {
                for (int i = 0; i < events.length(); i++) {
                    JSONObject e = events.optJSONObject(i);
                    if (e == null) continue;
                    String kind = e.optString("kind", "");
                    String text = e.optString("text", "");
                    db.addEvent(device, kind, text, e.optLong("ts", System.currentTimeMillis() / 1000L));
                    if ("sos".equals(kind)) notifySos(device, text);
                }
            }

            Db.Device d = db.device(device);
            resp.put("ok", true);
            resp.put("policy", d == null ? Db.defaultPolicy() : d.policy);
            resp.put("commands", db.pending(device));
            resp.put("server_ts", System.currentTimeMillis() / 1000L);
        } catch (Exception e) {
            try {
                resp.put("ok", false);
                resp.put("error", e.getClass().getSimpleName());
            } catch (Exception ignored) {}
        }
        return resp;
    }

    private JSONObject onAck(String device, String body) {
        JSONObject resp = new JSONObject();
        try {
            JSONObject a = new JSONObject(body);
            String id = a.optString("id", "");
            boolean ok = a.optBoolean("ok", false);
            String result = a.optString("result", "");
            db.ack(id, device, ok, result);
            if (!ok) db.addEvent(device, "command_failed", id + ": " + result, System.currentTimeMillis() / 1000L);
            resp.put("ok", true);
        } catch (Exception e) {
            try {
                resp.put("ok", false);
            } catch (Exception ignored) {}
        }
        return resp;
    }

    private void notifySos(String device, String text) {
        try {
            NotificationManager nm = (NotificationManager) ctx.getSystemService(Context.NOTIFICATION_SERVICE);
            if (nm == null) return;
            NotificationChannel ch = new NotificationChannel("hg_sos", "HomeGuard SOS",
                    NotificationManager.IMPORTANCE_HIGH);
            nm.createNotificationChannel(ch);
            int id = stableId(device);
            Intent i = new Intent(ctx, DeviceActivity.class).putExtra("device", device);
            PendingIntent pi = PendingIntent.getActivity(ctx, id, i,
                    PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
            String body = text == null ? "" : text;
            if (body.length() > 200) body = body.substring(0, 200) + "…";
            Notification.Builder b = new Notification.Builder(ctx, "hg_sos")
                    .setContentTitle("SOS от ребёнка")
                    .setContentText(body)
                    .setSmallIcon(android.R.drawable.stat_sys_warning)
                    .setAutoCancel(true)
                    .setContentIntent(pi);
            nm.notify(id, b.build());
        } catch (Exception ignored) {}
        // Optional local HA webhook (off unless configured in Settings).
        // Offload to a short-lived thread: never block the poll response.
        if (HaBridge.enabled(ctx)) {
            final String d = device, t = text;
            new Thread(new Runnable() {
                @Override
                public void run() {
                    HaBridge.send(ctx, d, t);
                }
            }, "hg-ha-bridge").start();
        }
    }

    private static int stableId(String device) {
        return (device == null ? 0 : device.hashCode()) & 0x7FFFFFFF;
    }

    private void respond(Socket s, int code, String json, Db.Device d, String path) throws Exception {
        byte[] out = json.getBytes("UTF-8");
        StringBuilder head = new StringBuilder();
        head.append("HTTP/1.1 ").append(code).append(code == 200 ? " OK" : " ERR").append("\r\n")
                .append("Content-Type: application/json; charset=utf-8\r\n")
                .append("Content-Length: ").append(out.length).append("\r\n")
                .append("Connection: close\r\n");
        if (code == 200 && d != null && d.secret != null) {
            String ts = String.valueOf(System.currentTimeMillis() / 1000L);
            String nonce = Protocol.nonce();
            head.append(Protocol.H_TS).append(": ").append(ts).append("\r\n")
                    .append(Protocol.H_NONCE).append(": ").append(nonce).append("\r\n")
                    .append(Protocol.H_SIG).append(": ")
                    .append(Protocol.signResponse(d.secret, path, ts, nonce, json)).append("\r\n");
        }
        head.append("\r\n");
        OutputStream os = s.getOutputStream();
        os.write(head.toString().getBytes("US-ASCII"));
        os.write(out);
        os.flush();
    }

    private static String readLine(InputStream in, long deadline) throws Exception {
        StringBuilder sb = new StringBuilder();
        int b;
        while (true) {
            if (System.currentTimeMillis() > deadline) {
                throw new java.net.SocketTimeoutException("request deadline");
            }
            b = in.read();
            if (b == -1) break;
            if (b == '\n') break;
            if (b != '\r') sb.append((char) b);
            if (sb.length() > MAX_LINE) throw new java.io.IOException("line too long");
        }
        if (b == -1 && sb.length() == 0) return null;
        return sb.toString();
    }

    private static byte[] readFully(InputStream in, int len, long deadline) throws Exception {
        byte[] buf = new byte[len];
        int off = 0;
        while (off < len) {
            if (System.currentTimeMillis() > deadline) {
                throw new java.net.SocketTimeoutException("body deadline");
            }
            int n = in.read(buf, off, len - off);
            if (n <= 0) throw new java.io.EOFException("short body");
            off += n;
        }
        return buf;
    }
}
