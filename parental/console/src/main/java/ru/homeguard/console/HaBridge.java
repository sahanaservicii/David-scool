package ru.homeguard.console;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONObject;

import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;

/**
 * Optional local bridge from the console to Home Assistant.
 *
 * No token is stored in the app: HA side is a webhook automation, so the only
 * thing the console keeps is the full webhook URL entered by the parent in
 * Settings. It is off by default and is only used when the parent enables it.
 *
 * All traffic stays inside LAN/WireGuard — no cloud, no FCM, no GitHub.
 */
public final class HaBridge {

    public static final String PREF_WEBHOOK_URL = "ha_webhook_url";

    private HaBridge() {}

    /** Reads the configured webhook URL. Empty string means disabled. */
    public static String url(Context c) {
        SharedPreferences p = c.getSharedPreferences("hg_console", Context.MODE_PRIVATE);
        return p.getString(PREF_WEBHOOK_URL, "").trim();
    }

    public static void setUrl(Context c, String value) {
        SharedPreferences p = c.getSharedPreferences("hg_console", Context.MODE_PRIVATE);
        p.edit().putString(PREF_WEBHOOK_URL, value == null ? "" : value.trim()).apply();
    }

    public static boolean enabled(Context c) {
        String u = url(c);
        return u.startsWith("http://") || u.startsWith("https://");
    }

    /**
     * Fire-and-forget POST of an SOS event to the HA webhook.
     * Never throws to the caller: SOS notification on the phone is primary.
     * Runs synchronously — callers must invoke it from a background thread.
     */
    public static boolean send(Context c, String device, String text) {
        if (!enabled(c)) return false;
        HttpURLConnection conn = null;
        try {
            JSONObject payload = new JSONObject();
            payload.put("device", device == null ? "" : device);
            payload.put("text", text == null ? "" : text);
            payload.put("ts", System.currentTimeMillis() / 1000L);
            byte[] body = payload.toString().getBytes("UTF-8");

            conn = (HttpURLConnection) new URL(url(c)).openConnection();
            conn.setRequestMethod("POST");
            conn.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            conn.setFixedLengthStreamingMode(body.length);
            conn.setConnectTimeout(4000);
            conn.setReadTimeout(4000);
            conn.setDoOutput(true);
            OutputStream os = conn.getOutputStream();
            try {
                os.write(body);
            } finally {
                os.close();
            }
            int code = conn.getResponseCode();
            return code >= 200 && code < 300;
        } catch (Exception ignored) {
            return false;
        } finally {
            if (conn != null) conn.disconnect();
        }
    }
}
