package ru.homeguard.agent;

import android.content.Context;

import org.json.JSONArray;
import org.json.JSONObject;

/**
 * Small persisted queue of notable events (lock/unlock/blocked/SOS).
 * Events are removed only after the console has acknowledged the sync, so an
 * SOS survives a network failure.
 */
public final class Event {

    private Event() {}

    public static synchronized void push(Context c, String kind, String text) {
        try {
            JSONArray a = load(c);
            JSONObject o = new JSONObject();
            o.put("kind", kind);
            o.put("text", text == null ? "" : text);
            o.put("ts", System.currentTimeMillis() / 1000L);
            a.put(o);
            while (a.length() > 60) {
                JSONArray b = new JSONArray();
                for (int i = 1; i < a.length(); i++) b.put(a.get(i));
                a = b;
            }
            Store.put(c, "events", a.toString());
        } catch (Exception ignored) {}
    }

    /** Snapshot without clearing. */
    public static synchronized JSONArray peek(Context c) {
        return load(c);
    }

    /** Drops the first {@code n} events, which the console has accepted. */
    public static synchronized void commit(Context c, int n) {
        if (n <= 0) return;
        JSONArray a = load(c);
        JSONArray b = new JSONArray();
        for (int i = n; i < a.length(); i++) b.put(a.opt(i));
        Store.put(c, "events", b.toString());
    }

    private static JSONArray load(Context c) {
        try {
            return new JSONArray(Store.get(c, "events", "[]"));
        } catch (Exception e) {
            return new JSONArray();
        }
    }
}
