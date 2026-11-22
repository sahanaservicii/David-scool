package ru.homeguard.agent;

import android.app.usage.UsageEvents;
import android.app.usage.UsageStats;
import android.app.usage.UsageStatsManager;
import android.content.Context;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.Calendar;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** Screen-time accounting through UsageStatsManager (no accessibility needed). */
public final class Usage {

    private Usage() {}

    public static long dayStart() {
        Calendar c = Calendar.getInstance();
        c.set(Calendar.HOUR_OF_DAY, 0);
        c.set(Calendar.MINUTE, 0);
        c.set(Calendar.SECOND, 0);
        c.set(Calendar.MILLISECOND, 0);
        return c.getTimeInMillis();
    }

    public static Map<String, Long> byPackage(Context ctx) {
        Map<String, Long> out = new HashMap<>();
        try {
            UsageStatsManager usm = (UsageStatsManager) ctx.getSystemService(Context.USAGE_STATS_SERVICE);
            if (usm == null) return out;
            long from = dayStart();
            long to = System.currentTimeMillis();
            List<UsageStats> stats = usm.queryUsageStats(UsageStatsManager.INTERVAL_DAILY, from, to);
            if (stats == null) return out;
            for (UsageStats s : stats) {
                long t = s.getTotalTimeInForeground();
                if (t > 0) out.put(s.getPackageName(), t);
            }
        } catch (Exception ignored) {}
        return out;
    }

    public static long totalMs(Context ctx) {
        long sum = 0;
        for (long v : byPackage(ctx).values()) sum += v;
        return sum;
    }

    public static JSONArray usageJson(Context ctx, int limit) {
        Map<String, Long> map = byPackage(ctx);
        JSONArray arr = new JSONArray();
        map.entrySet().stream()
                .sorted((a, b) -> Long.compare(b.getValue(), a.getValue()))
                .limit(limit)
                .forEach(e -> {
                    try {
                        JSONObject o = new JSONObject();
                        o.put("pkg", e.getKey());
                        o.put("min", e.getValue() / 60000L);
                        arr.put(o);
                    } catch (Exception ignored) {}
                });
        return arr;
    }

    /** Best-effort foreground package for the last 10 minutes. */
    public static String foregroundPackage(Context ctx) {
        try {
            UsageStatsManager usm = (UsageStatsManager) ctx.getSystemService(Context.USAGE_STATS_SERVICE);
            if (usm == null) return "";
            long now = System.currentTimeMillis();
            UsageEvents ev = usm.queryEvents(now - 10 * 60 * 1000L, now);
            if (ev == null) return "";
            UsageEvents.Event e = new UsageEvents.Event();
            String last = "";
            while (ev.hasNextEvent()) {
                ev.getNextEvent(e);
                if (e.getEventType() == UsageEvents.Event.MOVE_TO_FOREGROUND
                        || e.getEventType() == UsageEvents.Event.ACTIVITY_RESUMED) {
                    last = e.getPackageName();
                }
            }
            return last;
        } catch (Exception e) {
            return "";
        }
    }
}
