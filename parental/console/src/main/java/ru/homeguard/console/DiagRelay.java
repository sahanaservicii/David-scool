package ru.homeguard.console;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONObject;

import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Temporary diagnostic relay: posts redacted logs/payloads to a user-provided URL. */
public final class DiagRelay {

    private static final String PREF = "hg_console";
    private static final String KEY_URL = "diag_relay_url";
    private static final String KEY_ON = "diag_relay_on";
    private static final ExecutorService EX = Executors.newSingleThreadExecutor();

    private DiagRelay() {}

    public static String url(Context c) {
        return c.getSharedPreferences(PREF, Context.MODE_PRIVATE).getString(KEY_URL, "").trim();
    }

    public static boolean enabled(Context c) {
        SharedPreferences p = c.getSharedPreferences(PREF, Context.MODE_PRIVATE);
        return p.getBoolean(KEY_ON, false) && isHttp(url(c));
    }

    public static void set(Context c, String url, boolean on) {
        c.getSharedPreferences(PREF, Context.MODE_PRIVATE).edit()
                .putString(KEY_URL, url == null ? "" : url.trim())
                .putBoolean(KEY_ON, on)
                .apply();
    }

    private static boolean isHttp(String u) {
        return u != null && (u.startsWith("http://") || u.startsWith("https://"));
    }

    public static void send(final Context c, final String kind, final String message, final String payload) {
        if (c == null || !enabled(c)) return;
        final String u = url(c);
        final long ts = System.currentTimeMillis();
        EX.execute(new Runnable() {
            @Override public void run() { post(u, ts, kind, message, payload); }
        });
    }

    private static void post(String endpoint, long ts, String kind, String message, String payload) {
        HttpURLConnection conn = null;
        try {
            JSONObject o = new JSONObject();
            o.put("src", "console");
            o.put("ts", ts);
            o.put("kind", kind == null ? "" : kind);
            o.put("message", redact(message));
            if (payload != null && !payload.isEmpty()) o.put("payload", redact(payload));
            byte[] body = o.toString().getBytes("UTF-8");
            conn = (HttpURLConnection) new URL(endpoint).openConnection();
            conn.setRequestMethod("POST");
            conn.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            conn.setConnectTimeout(4000);
            conn.setReadTimeout(4000);
            conn.setDoOutput(true);
            conn.setFixedLengthStreamingMode(body.length);
            OutputStream os = conn.getOutputStream();
            try { os.write(body); } finally { os.close(); }
            conn.getResponseCode();
        } catch (Exception ignored) {
        } finally {
            if (conn != null) conn.disconnect();
        }
    }

    public static String redact(String s) {
        if (s == null) return "";
        String r = s;
        r = r.replaceAll("(hg1:[^:\\s]+:[^:\\s]+:[^:\\s]+:)[A-Z2-9-]{8,}", "$1<redacted>");
        r = r.replaceAll("(?i)(\"(?:secret|code|pairing|token|password|x-hg-sig)\"\\s*:\\s*\")[^\"]*(\")", "$1<redacted>$2");
        r = r.replaceAll("(?i)(\"(?:secret|code|pairing|token|password|x-hg-sig)\"\\s*:\\s*)([0-9]+)", "$1\"<redacted>\"");
        r = r.replaceAll("(?i)(X-HG-Sig\\s*[:=]\\s*)[a-f0-9]{16,}", "$1<redacted>");
        if (r.length() > 4000) r = r.substring(0, 4000) + "…<truncated>";
        return r;
    }
}
