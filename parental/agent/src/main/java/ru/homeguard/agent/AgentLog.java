package ru.homeguard.agent;

import java.text.SimpleDateFormat;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Date;
import java.util.Deque;
import java.util.List;
import java.util.Locale;

/** In-memory ring buffer for agent diagnostics. No secrets, no pairing codes. */
public final class AgentLog {

    public static final class Entry {
        public final long ts;
        public final String level; // I/W/E
        public final String tag;
        public final String text;
        Entry(long ts, String level, String tag, String text) {
            this.ts = ts; this.level = level; this.tag = tag; this.text = text;
        }
        String line() {
            String t = new SimpleDateFormat("HH:mm:ss.SSS", Locale.US).format(new Date(ts));
            return t + " " + level + "/" + tag + ": " + text;
        }
    }

    private static final int MAX = 400;
    private static final Deque<Entry> BUF = new ArrayDeque<>();

    private AgentLog() {}

    public static synchronized void i(String tag, String text) { add("I", tag, text); }
    public static synchronized void w(String tag, String text) { add("W", tag, text); }
    public static synchronized void e(String tag, String text) { add("E", tag, text); }

    private static void add(String level, String tag, String text) {
        String tg = tag == null ? "app" : tag.replaceAll("[\\r\\n\\t]+", " ").trim();
        String t = text == null ? "" : text.replaceAll("[\\r\\n\\t]+", " ").trim();
        if (tg.length() > 24) tg = tg.substring(0, 24);
        if (t.length() > 300) t = t.substring(0, 300) + "…";
        BUF.addLast(new Entry(System.currentTimeMillis(), level, tg, t));
        while (BUF.size() > MAX) BUF.removeFirst();
    }

    public static synchronized List<Entry> snapshot() {
        return new ArrayList<>(BUF);
    }

    public static synchronized String dump() {
        StringBuilder sb = new StringBuilder();
        for (Entry e : BUF) sb.append(e.line()).append('\n');
        return sb.toString();
    }

    public static synchronized void clear() { BUF.clear(); }
}
