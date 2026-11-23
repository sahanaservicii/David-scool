package ru.homeguard.console;

import java.text.SimpleDateFormat;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Date;
import java.util.Deque;
import java.util.List;
import java.util.Locale;

/** In-memory ring buffer for live diagnostics. No secrets, no payloads. */
public final class ServerLog {

    public static final class Entry {
        public final long ts;
        public final String level; // I/W/E
        public final String text;
        Entry(long ts, String level, String text) {
            this.ts = ts; this.level = level; this.text = text;
        }
        String line() {
            String t = new SimpleDateFormat("HH:mm:ss", Locale.US).format(new Date(ts));
            return t + " " + level + " " + text;
        }
    }

    private static final int MAX = 300;
    private static final Deque<Entry> BUF = new ArrayDeque<>();

    private ServerLog() {}

    public static synchronized void i(String text) { add("I", text); }
    public static synchronized void w(String text) { add("W", text); }
    public static synchronized void e(String text) { add("E", text); }

    private static void add(String level, String text) {
        String t = text == null ? "" : text.replaceAll("[\\r\\n\\t]+", " ").trim();
        if (t.length() > 240) t = t.substring(0, 240) + "…";
        BUF.addLast(new Entry(System.currentTimeMillis(), level, t));
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
