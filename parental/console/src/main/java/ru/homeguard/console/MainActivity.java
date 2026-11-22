package ru.homeguard.console;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.View;
import android.view.ViewGroup;
import android.widget.LinearLayout;
import android.widget.ScrollView;

import org.json.JSONObject;

import java.util.Calendar;
import java.util.List;

/** Tab 1: overview. Today's total, children cards, quick add. */
public class MainActivity extends Activity {

    private final Handler h = new Handler(Looper.getMainLooper());
    private LinearLayout summary;
    private LinearLayout list;

    private final Runnable refresh = new Runnable() {
        @Override
        public void run() {
            render();
            h.postDelayed(this, 3000L);
        }
    };

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        ConsoleService.start(this);

        ScrollView sc = Ui.scroll(this);
        LinearLayout body = Ui.body(sc);

        summary = Ui.col(this);
        body.addView(Ui.sectionTitle(this, "Дети"));
        list = Ui.col(this);
        body.addView(list);

        body.addView(Ui.primary(this, "Добавить ребёнка", new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                startActivity(new Intent(MainActivity.this, PairingActivity.class));
            }
        }), margin(18));

        setContentView(Ui.page(this,
                Ui.header(this, "HOME GUARD", greeting(),
                        "Локальная консоль · данные остаются дома", summary),
                sc, Ui.TAB_HOME));

        requestPerms();
    }

    private void requestPerms() {
        try {
            if (checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS)
                    != android.content.pm.PackageManager.PERMISSION_GRANTED) {
                requestPermissions(new String[]{android.Manifest.permission.POST_NOTIFICATIONS}, 1);
            }
        } catch (Exception ignored) {}
    }

    @Override
    protected void onResume() {
        super.onResume();
        h.post(refresh);
    }

    @Override
    protected void onPause() {
        super.onPause();
        h.removeCallbacks(refresh);
    }

    private LinearLayout.LayoutParams margin(int dp) {
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        lp.topMargin = Ui.dp(this, dp);
        return lp;
    }

    private LinearLayout.LayoutParams weight() {
        return new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
    }

    private static String greeting() {
        int hour = Calendar.getInstance().get(Calendar.HOUR_OF_DAY);
        if (hour < 5) return "Доброй ночи";
        if (hour < 12) return "Доброе утро";
        if (hour < 18) return "Добрый день";
        return "Добрый вечер";
    }

    private void render() {
        List<Db.Device> devices = Db.get(this).devices();
        int online = 0;
        long today = 0;
        for (Db.Device d : devices) {
            if (d.online()) online++;
            today += d.state().optInt("today_min", 0);
        }
        int events = Db.get(this).eventsSince(null,
                System.currentTimeMillis() / 1000L - 86400L);

        summary.removeAllViews();
        summary.addView(summaryCard(devices.size(), online, today, events));

        list.removeAllViews();
        if (devices.isEmpty()) {
            list.addView(emptyCard(), margin(12));
            return;
        }
        for (Db.Device d : devices) {
            list.addView(childCard(d), margin(12));
        }
    }

    private View summaryCard(int kids, int online, long todayMin, int events) {
        LinearLayout card = Ui.glassCard(this);
        LinearLayout top = Ui.row(this);

        LinearLayout left = Ui.col(this);
        left.addView(Ui.txt(this, Ui.minutes(todayMin), 30, 0xFFFFFFFF, true));
        left.addView(Ui.txt(this, "экранное время сегодня", 12.5f, 0xD9FFFFFF, false));
        top.addView(left, weight());

        boolean alive = ConsoleService.alive;
        top.addView(Ui.pill(this, alive ? "сервер работает" : "сервер выключен",
                alive ? 0xFFFFFFFF : 0xFFFFFFFF,
                alive ? 0x3322C55E : 0x33EF4444));
        card.addView(top);

        View div = new View(this);
        div.setBackgroundColor(0x33FFFFFF);
        LinearLayout.LayoutParams dlp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 1);
        dlp.topMargin = Ui.dp(this, 14);
        card.addView(div, dlp);

        LinearLayout stats = Ui.row(this);
        stats.setPadding(0, Ui.dp(this, 12), 0, 0);
        stats.addView(statCol("дети", kids == 0 ? "—" : online + " / " + kids), weight());
        stats.addView(statCol("события за сутки", String.valueOf(events)), weight());
        stats.addView(statCol("порт", String.valueOf(ControlServer.PORT)), weight());
        card.addView(stats);
        return card;
    }

    private LinearLayout statCol(String label, String value) {
        LinearLayout c = Ui.col(this);
        c.addView(Ui.txt(this, value, 15, 0xFFFFFFFF, true));
        c.addView(Ui.txt(this, label, 11, 0xB3FFFFFF, false));
        return c;
    }

    private LinearLayout childCard(final Db.Device d) {
        JSONObject st = d.state();
        LinearLayout card = Ui.card(this);
        card.setBackground(Ui.ripple(this, Ui.round(this, Ui.SURFACE, 20), 0x224C6FFF));
        card.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                Intent i = new Intent(MainActivity.this, DeviceActivity.class);
                i.putExtra("device", d.id);
                startActivity(i);
            }
        });

        LinearLayout top = Ui.row(this);
        top.addView(Ui.avatar(this, d.name, 46));

        LinearLayout col = Ui.col(this);
        col.setPadding(Ui.dp(this, 12), 0, 0, 0);
        col.addView(Ui.txt(this, d.name, 16, Ui.INK, true));
        String sub;
        if (d.online()) sub = "на связи";
        else if (d.lastSeen > 0) sub = "офлайн · " + Util.ago(d.lastSeen);
        else sub = "ещё не подключался";
        col.addView(Ui.txt(this, sub, 12.5f, d.online() ? Ui.GREEN : Ui.MUTED, false));
        top.addView(col, weight());

        int battery = st.optInt("battery", -1);
        if (battery >= 0) {
            int tint = battery < 15 ? Ui.RED : battery < 35 ? Ui.ORANGE : Ui.GREEN;
            top.addView(Ui.pill(this, battery + "%", tint, Ui.alpha(tint, 0x1A)));
        }
        card.addView(top);

        long today = st.optInt("today_min", 0);
        int limit = d.policy.optInt("daily_limit_min", 0);
        long base = limit > 0 ? limit : 240;
        float pct = Math.max(0f, Math.min(1f, today / (float) base));
        Ui.Progress bar = new Ui.Progress(this);
        bar.set(pct, pct > 0.9f ? Ui.RED : pct > 0.7f ? Ui.ORANGE : Ui.BLUE);
        LinearLayout.LayoutParams blp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, Ui.dp(this, 8));
        blp.topMargin = Ui.dp(this, 14);
        card.addView(bar, blp);

        LinearLayout caption = Ui.row(this);
        caption.setPadding(0, Ui.dp(this, 8), 0, 0);
        caption.addView(Ui.txt(this, Ui.minutes(today) + " экрана", 12, Ui.INK2, false), weight());
        caption.addView(Ui.txt(this, limit > 0 ? "лимит " + Ui.minutes(limit) : "без лимита",
                12, Ui.MUTED, false));
        card.addView(caption);

        return card;
    }

    private View emptyCard() {
        LinearLayout card = Ui.card(this);
        card.setGravity(android.view.Gravity.CENTER_HORIZONTAL);
        card.setPadding(Ui.dp(this, 20), Ui.dp(this, 26), Ui.dp(this, 20), Ui.dp(this, 24));

        android.widget.ImageView iv = new android.widget.ImageView(this);
        iv.setImageResource(R.drawable.ic_shield);
        iv.setColorFilter(Ui.BLUE);
        card.addView(iv, new LinearLayout.LayoutParams(Ui.dp(this, 46), Ui.dp(this, 46)));

        android.widget.TextView t = Ui.txt(this, "Пока нет детей", 17, Ui.INK, true);
        t.setPadding(0, Ui.dp(this, 12), 0, 0);
        card.addView(t);

        android.widget.TextView s = Ui.txt(this,
                "Установите агент на телефон ребёнка и введите код привязки. "
                        + "Всё работает внутри вашей сети, без облака.", 13, Ui.MUTED, false);
        s.setGravity(android.view.Gravity.CENTER);
        s.setPadding(0, Ui.dp(this, 8), 0, 0);
        card.addView(s);
        return card;
    }
}
