package ru.homeguard.console;

import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;

import org.json.JSONArray;
import org.json.JSONObject;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.UUID;

/** Local store: devices, policies, queued commands, events, usage. */
public class Db extends SQLiteOpenHelper {

    public static final class Device {
        public String id;
        public String name;
        public String secret;
        public String lastJson;
        public long lastSeen;
        public JSONObject policy = new JSONObject();
        public int policyV;

        public JSONObject state() {
            try {
                return lastJson == null ? new JSONObject() : new JSONObject(lastJson);
            } catch (Exception e) {
                return new JSONObject();
            }
        }

        public boolean online() {
            return System.currentTimeMillis() / 1000L - lastSeen < 200;
        }
    }

    private static Db INSTANCE;

    public static synchronized Db get(Context c) {
        if (INSTANCE == null) INSTANCE = new Db(c.getApplicationContext());
        return INSTANCE;
    }

    /** Bump together with a migration step in onUpgrade(). */
    public static final int DB_VERSION = 2;

    private Db(Context c) {
        super(c, "homeguard.db", null, DB_VERSION);
    }

    @Override
    public void onCreate(SQLiteDatabase db) {
        db.execSQL("CREATE TABLE devices(id TEXT PRIMARY KEY, name TEXT, secret TEXT, policy TEXT,"
                + " policy_v INTEGER, last_json TEXT, last_seen INTEGER, created INTEGER)");
        db.execSQL("CREATE TABLE commands(id TEXT PRIMARY KEY, device TEXT, type TEXT, args TEXT,"
                + " state TEXT, created INTEGER, result TEXT)");
        db.execSQL("CREATE TABLE events(id INTEGER PRIMARY KEY AUTOINCREMENT, device TEXT, kind TEXT,"
                + " text TEXT, ts INTEGER)");
        db.execSQL("CREATE TABLE usage(device TEXT, day TEXT, pkg TEXT, ms INTEGER,"
                + " PRIMARY KEY(device, day, pkg))");
        db.execSQL("CREATE INDEX idx_cmd_device ON commands(device, state)");
        db.execSQL("CREATE INDEX idx_ev_ts ON events(ts)");
        db.execSQL("CREATE UNIQUE INDEX idx_ev_unique ON events(device, ts, kind, text)");
        db.execSQL("CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT)");
    }

    @Override
    public void onUpgrade(SQLiteDatabase db, int oldV, int newV) {
        if (oldV < 2) {
            // 1 -> 2: a resent event must not duplicate in the feed, plus a meta table.
            db.execSQL("DELETE FROM events WHERE id NOT IN ("
                    + "SELECT MIN(id) FROM events GROUP BY device, ts, kind, text)");
            db.execSQL("CREATE UNIQUE INDEX IF NOT EXISTS idx_ev_unique"
                    + " ON events(device, ts, kind, text)");
            db.execSQL("CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT)");
        }
    }

    // ---------------- devices ----------------

    public void addDevice(String id, String name, String secretCode) {
        JSONObject p = defaultPolicy();
        ContentValues v = new ContentValues();
        v.put("id", id);
        v.put("name", name);
        v.put("secret", Seal.get().seal(Protocol.normalizeCode(secretCode)));
        v.put("policy", p.toString());
        v.put("policy_v", p.optInt("v", 1));
        v.put("last_seen", 0);
        v.put("created", System.currentTimeMillis() / 1000L);
        getWritableDatabase().insertWithOnConflict("devices", null, v, SQLiteDatabase.CONFLICT_REPLACE);
    }

    public void removeDevice(String id) {
        getWritableDatabase().delete("devices", "id=?", new String[]{id});
        getWritableDatabase().delete("commands", "device=?", new String[]{id});
        getWritableDatabase().delete("events", "device=?", new String[]{id});
        getWritableDatabase().delete("usage", "device=?", new String[]{id});
    }

    public List<Device> devices() {
        List<Device> out = new ArrayList<>();
        try (Cursor c = getReadableDatabase().rawQuery("SELECT id,name,secret,policy,policy_v,last_json,last_seen"
                + " FROM devices ORDER BY name", null)) {
            while (c.moveToNext()) out.add(read(c));
        }
        return out;
    }

    public Device device(String id) {
        try (Cursor c = getReadableDatabase().rawQuery("SELECT id,name,secret,policy,policy_v,last_json,last_seen"
                + " FROM devices WHERE id=?", new String[]{id})) {
            return c.moveToFirst() ? read(c) : null;
        }
    }

    private Device read(Cursor c) {
        Device d = new Device();
        d.id = c.getString(0);
        d.name = c.getString(1);
        d.secret = Seal.get().open(c.getString(2));
        try {
            d.policy = new JSONObject(c.getString(3) == null ? "{}" : c.getString(3));
        } catch (Exception ignored) {}
        d.policyV = c.getInt(4);
        d.lastJson = c.getString(5);
        d.lastSeen = c.getLong(6);
        return d;
    }

    // ---------------- state ----------------

    public void saveState(String id, String json) {
        ContentValues v = new ContentValues();
        v.put("last_json", json);
        v.put("last_seen", System.currentTimeMillis() / 1000L);
        getWritableDatabase().update("devices", v, "id=?", new String[]{id});
    }

    public void saveUsage(String id, JSONArray usage) {
        String day = new SimpleDateFormat("yyyy-MM-dd", Locale.US).format(new Date());
        SQLiteDatabase db = getWritableDatabase();
        for (int i = 0; i < usage.length(); i++) {
            JSONObject o = usage.optJSONObject(i);
            if (o == null) continue;
            ContentValues v = new ContentValues();
            v.put("device", id);
            v.put("day", day);
            v.put("pkg", o.optString("pkg", "?"));
            long min = Math.max(0L, Math.min(1440L, o.optLong("min", 0)));
            v.put("ms", min * 60000L);
            db.insertWithOnConflict("usage", null, v, SQLiteDatabase.CONFLICT_REPLACE);
        }
    }

    public JSONArray usage(String device, String day) {
        JSONArray arr = new JSONArray();
        try (Cursor c = getReadableDatabase().rawQuery(
                "SELECT pkg,ms FROM usage WHERE device=? AND day=? ORDER BY ms DESC LIMIT 20",
                new String[]{device, day})) {
            while (c.moveToNext()) {
                JSONObject o = new JSONObject();
                o.put("pkg", c.getString(0));
                o.put("min", c.getLong(1) / 60000L);
                arr.put(o);
            }
        } catch (Exception ignored) {}
        return arr;
    }

    // ---------------- policy ----------------

    public void savePolicy(String device, JSONObject policy) {
        int v = policy.optInt("v", 1);
        ContentValues cv = new ContentValues();
        cv.put("policy", policy.toString());
        cv.put("policy_v", v);
        getWritableDatabase().update("devices", cv, "id=?", new String[]{device});
    }

    public static JSONObject defaultPolicy() {
        JSONObject p = new JSONObject();
        try {
            p.put("v", 1);
            p.put("install_apps", true);
            p.put("install_unknown", false);
            p.put("uninstall_apps", true);
            p.put("wifi_config", true);
            p.put("bluetooth", true);
            p.put("usb", false);
            p.put("camera", true);
            p.put("screen_capture", true);
            p.put("status_bar", true);
            p.put("keyguard", true);
            p.put("safe_boot", false);
            p.put("factory_reset", false);
            p.put("debug", false);
            p.put("apps_control", true);
            p.put("blocked", new JSONArray());
            p.put("hidden_blocked", false);
            p.put("curfew", new JSONArray());
            p.put("daily_limit_min", 0);
            p.put("kiosk", new JSONObject().put("enabled", false).put("packages", new JSONArray()));
            p.put("lock_now", false);
            p.put("grant_permissions", true);
        } catch (Exception ignored) {}
        return p;
    }

    // ---------------- commands ----------------

    public String queueCommand(String device, String type, JSONObject args) {
        String id = UUID.randomUUID().toString().replace("-", "");
        ContentValues v = new ContentValues();
        v.put("id", id);
        v.put("device", device);
        v.put("type", type);
        v.put("args", args == null ? "{}" : args.toString());
        v.put("state", "PENDING");
        v.put("created", System.currentTimeMillis() / 1000L);
        getWritableDatabase().insert("commands", null, v);
        return id;
    }

    public JSONArray pending(String device) {
        // Re-deliver commands that were handed out but never acknowledged.
        ContentValues stale = new ContentValues();
        stale.put("state", "PENDING");
        getWritableDatabase().update("commands", stale, "device=? AND state='SENT' AND created<?",
                new String[]{device, String.valueOf(System.currentTimeMillis() / 1000L - 600)});

        JSONArray out = new JSONArray();
        List<String> ids = new ArrayList<>();
        try (Cursor c = getReadableDatabase().rawQuery(
                "SELECT id,type,args FROM commands WHERE device=? AND state='PENDING'"
                        + " ORDER BY created LIMIT 20", new String[]{device})) {
            while (c.moveToNext()) {
                JSONObject o = new JSONObject();
                o.put("id", c.getString(0));
                o.put("type", c.getString(1));
                try {
                    o.put("args", new JSONObject(c.getString(2)));
                } catch (Exception e) {
                    o.put("args", new JSONObject());
                }
                ids.add(c.getString(0));
                out.put(o);
            }
        } catch (Exception ignored) {}
        for (String id : ids) {
            ContentValues v = new ContentValues();
            v.put("state", "SENT");
            v.put("created", System.currentTimeMillis() / 1000L);
            getWritableDatabase().update("commands", v, "id=?", new String[]{id});
        }
        return out;
    }

    public void ack(String id, String device, boolean ok, String result) {
        ContentValues v = new ContentValues();
        v.put("state", ok ? "DONE" : "FAILED");
        v.put("result", result == null ? "" : result);
        getWritableDatabase().update("commands", v, "id=? AND device=?",
                new String[]{id, device == null ? "" : device});
    }

    // ---------------- events ----------------

    public void addEvent(String device, String kind, String text, long ts) {
        ContentValues v = new ContentValues();
        v.put("device", device);
        v.put("kind", kind);
        v.put("text", text);
        v.put("ts", ts);
        // Unique index (device, ts, kind, text): a resent event is ignored, not duplicated.
        getWritableDatabase().insertWithOnConflict("events", null, v,
                SQLiteDatabase.CONFLICT_IGNORE);
    }

    public List<String[]> events(String device, int limit) {
        List<String[]> out = new ArrayList<>();
        String sql = "SELECT device,kind,text,ts FROM events" + (device == null ? "" : " WHERE device=?")
                + " ORDER BY ts DESC LIMIT ?";
        String[] args = device == null
                ? new String[]{String.valueOf(Math.max(1, limit))}
                : new String[]{device, String.valueOf(Math.max(1, limit))};
        try (Cursor c = getReadableDatabase().rawQuery(sql, args)) {
            while (c.moveToNext()) {
                out.add(new String[]{c.getString(0), c.getString(1), c.getString(2),
                        String.valueOf(c.getLong(3))});
            }
        }
        return out;
    }

    /** Screen time per day, oldest first. device==null means all children. */
    public long[] usageByDay(String device, int days) {
        int n = Math.max(1, days);
        long[] out = new long[n];
        SimpleDateFormat f = new SimpleDateFormat("yyyy-MM-dd", Locale.US);
        java.util.Calendar cal = java.util.Calendar.getInstance();
        for (int i = n - 1; i >= 0; i--) {
            String day = f.format(cal.getTime());
            String sql = "SELECT SUM(ms) FROM usage WHERE day=?"
                    + (device == null ? "" : " AND device=?");
            try (Cursor c = getReadableDatabase().rawQuery(sql,
                    device == null ? new String[]{day} : new String[]{day, device})) {
                out[i] = c.moveToFirst() ? c.getLong(0) : 0L;
            }
            cal.add(java.util.Calendar.DAY_OF_MONTH, -1);
        }
        return out;
    }

    /** Today's usage merged across all children. */
    public JSONArray usageAll(String day) {
        JSONArray arr = new JSONArray();
        try (Cursor c = getReadableDatabase().rawQuery(
                "SELECT pkg,SUM(ms) FROM usage WHERE day=? GROUP BY pkg ORDER BY SUM(ms) DESC LIMIT 20",
                new String[]{day})) {
            while (c.moveToNext()) {
                JSONObject o = new JSONObject();
                o.put("pkg", c.getString(0));
                o.put("min", c.getLong(1) / 60000L);
                arr.put(o);
            }
        } catch (Exception ignored) {}
        return arr;
    }

    public int eventsSince(String device, long sinceSec) {
        String sql = "SELECT COUNT(*) FROM events WHERE ts>=?"
                + (device == null ? "" : " AND device=?");
        try (Cursor c = getReadableDatabase().rawQuery(sql,
                device == null ? new String[]{String.valueOf(sinceSec)}
                        : new String[]{String.valueOf(sinceSec), device})) {
            return c.moveToFirst() ? c.getInt(0) : 0;
        }
    }

    // ---------------- housekeeping ----------------

    /** Retention: keeps the console small and predictable. Runs at most once a day. */
    public void prune() {
        String today = new SimpleDateFormat("yyyy-MM-dd", Locale.US).format(new Date());
        if (today.equals(meta("pruned"))) return;
        SQLiteDatabase db = getWritableDatabase();
        long cutoff = System.currentTimeMillis() / 1000L - 120L * 86400L;
        db.delete("events", "ts<?", new String[]{String.valueOf(cutoff)});
        db.delete("usage", "day<?", new String[]{isoDaysAgo(400)});
        db.delete("commands", "state IN ('DONE','FAILED') AND created<?",
                new String[]{String.valueOf(System.currentTimeMillis() / 1000L - 30L * 86400L)});
        metaPut("pruned", today);
    }

    public String meta(String key) {
        try (Cursor c = getReadableDatabase().rawQuery(
                "SELECT value FROM meta WHERE key=?", new String[]{key})) {
            return c.moveToFirst() ? c.getString(0) : null;
        } catch (Exception e) {
            return null;
        }
    }

    public void metaPut(String key, String value) {
        ContentValues v = new ContentValues();
        v.put("key", key);
        v.put("value", value);
        getWritableDatabase().insertWithOnConflict("meta", null, v,
                SQLiteDatabase.CONFLICT_REPLACE);
    }

    private static String isoDaysAgo(int days) {
        Calendar cal = Calendar.getInstance();
        cal.add(Calendar.DAY_OF_MONTH, -days);
        return new SimpleDateFormat("yyyy-MM-dd", Locale.US).format(cal.getTime());
    }

    // ---------------- backup / restore ----------------

    public JSONArray exportEvents(int days) {
        JSONArray out = new JSONArray();
        long since = System.currentTimeMillis() / 1000L - Math.max(1, days) * 86400L;
        try (Cursor c = getReadableDatabase().rawQuery(
                "SELECT device,kind,text,ts FROM events WHERE ts>=? ORDER BY ts",
                new String[]{String.valueOf(since)})) {
            while (c.moveToNext()) {
                JSONArray row = new JSONArray();
                row.put(c.getString(0));
                row.put(c.getString(1));
                row.put(c.getString(2));
                row.put(c.getLong(3));
                out.put(row);
            }
        }
        return out;
    }

    public JSONArray exportUsage(int days) {
        JSONArray out = new JSONArray();
        try (Cursor c = getReadableDatabase().rawQuery(
                "SELECT device,day,pkg,ms FROM usage WHERE day>=? ORDER BY day",
                new String[]{isoDaysAgo(days)})) {
            while (c.moveToNext()) {
                JSONArray row = new JSONArray();
                row.put(c.getString(0));
                row.put(c.getString(1));
                row.put(c.getString(2));
                row.put(c.getLong(3));
                out.put(row);
            }
        }
        return out;
    }

    /**
     * Restores one child. The pairing code arrives in plaintext inside the encrypted
     * backup and is sealed again with this phone's Keystore key.
     */
    public void restoreDevice(String id, String name, String code, JSONObject policy,
                              int policyV, long lastSeen) {
        ContentValues v = new ContentValues();
        v.put("id", id);
        v.put("name", name);
        v.put("secret", Seal.get().seal(Protocol.normalizeCode(code)));
        JSONObject p = policy == null ? defaultPolicy() : policy;
        v.put("policy", p.toString());
        v.put("policy_v", policyV <= 0 ? p.optInt("v", 1) : policyV);
        v.put("last_seen", lastSeen);
        v.put("created", System.currentTimeMillis() / 1000L);
        getWritableDatabase().insertWithOnConflict("devices", null, v,
                SQLiteDatabase.CONFLICT_REPLACE);
    }

    public void restoreEvent(String device, String kind, String text, long ts) {
        addEvent(device, kind, text, ts);
    }

    public void restoreUsage(String device, String day, String pkg, long ms) {
        ContentValues v = new ContentValues();
        v.put("device", device);
        v.put("day", day);
        v.put("pkg", pkg);
        v.put("ms", ms);
        getWritableDatabase().insertWithOnConflict("usage", null, v,
                SQLiteDatabase.CONFLICT_REPLACE);
    }

    public void clearAll() {
        SQLiteDatabase db = getWritableDatabase();
        db.delete("devices", null, null);
        db.delete("commands", null, null);
        db.delete("events", null, null);
        db.delete("usage", null, null);
    }
}
