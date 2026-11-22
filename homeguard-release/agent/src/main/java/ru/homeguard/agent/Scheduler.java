package ru.homeguard.agent;

import android.os.Build;
import android.os.Handler;
import android.os.Looper;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.Calendar;

/** Evaluates curfew windows and the daily screen-time limit once a minute. */
public final class Scheduler {

    private static final Handler H = new Handler(Looper.getMainLooper());
    private static Runnable loop;

    private Scheduler() {}

    public static void start(final android.content.Context ctx) {
        if (loop != null) return;
        loop = new Runnable() {
            @Override
            public void run() {
                try {
                    tick(ctx.getApplicationContext());
                } catch (Exception ignored) {}
                H.postDelayed(this, 60_000L);
            }
        };
        H.post(loop);
    }

    public static void tick(android.content.Context c) {
        JSONObject policy = policy(c);
        if (policy == null) return;

        String reason = null;

        JSONArray curfew = policy.optJSONArray("curfew");
        if (curfew != null && inWindow(curfew)) reason = "curfew";

        int limit = policy.optInt("daily_limit_min", 0);
        if (reason == null && limit > 0) {
            long used = Usage.totalMs(c) / 60000L;
            if (used >= limit) reason = "daily_limit";
        }
        if (policy.optBoolean("lock_now", false)) reason = "parent";

        boolean override = Store.getLong(c, "manual_override", 0) > System.currentTimeMillis();
        if (override) reason = null;

        if (reason != null) {
            if (!LockState.locked) {
                LockState.lock(reason);
                CurfewActivity.show(c, reason);
                Admin.lockNow(c);
                Event.push(c, "lock", reason);
            }
        } else if (LockState.locked && !"parent".equals(LockState.reason)) {
            LockState.unlock();
            CurfewActivity.hide(c);
            Event.push(c, "unlock", "schedule");
        }
    }

    public static JSONObject policy(android.content.Context c) {
        String raw = Store.get(c, "policy", null);
        if (raw == null) return null;
        try {
            return new JSONObject(raw);
        } catch (Exception e) {
            return null;
        }
    }

    private static boolean inWindow(JSONArray windows) {
        Calendar now = Calendar.getInstance();
        int dow = now.get(Calendar.DAY_OF_WEEK) - 1; // 0 = Sunday
        int mins = now.get(Calendar.HOUR_OF_DAY) * 60 + now.get(Calendar.MINUTE);
        for (int i = 0; i < windows.length(); i++) {
            JSONObject w = windows.optJSONObject(i);
            if (w == null) continue;
            if (!dayMatches(w.optJSONArray("days"), dow)) continue;
            int from = parse(w.optString("from", "00:00"));
            int to = parse(w.optString("to", "00:00"));
            if (from == to) continue;
            if (from < to) {
                if (mins >= from && mins < to) return true;
            } else {
                // window crosses midnight: evening part, or early-morning part of the next day
                if (mins >= from || mins < to) return true;
            }
        }
        return false;
    }

    private static boolean dayMatches(JSONArray days, int dow) {
        if (days == null || days.length() == 0) return true;
        for (int i = 0; i < days.length(); i++) if (days.optInt(i, -1) == dow) return true;
        return false;
    }

    private static int parse(String hhmm) {
        try {
            String[] p = hhmm.split(":");
            return Integer.parseInt(p[0]) * 60 + Integer.parseInt(p[1]);
        } catch (Exception e) {
            return 0;
        }
    }

    public static String describe() {
        return "sdk=" + Build.VERSION.SDK_INT;
    }
}
