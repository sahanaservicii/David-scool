package ru.homeguard.console;

import android.app.Activity;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.View;
import android.view.ViewGroup;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import org.json.JSONArray;
import org.json.JSONObject;

import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.Date;
import java.util.List;
import java.util.Locale;

/** Tab 3: seven-day chart and the top apps. */
public class ReportsActivity extends Activity {

    private final Handler h = new Handler(Looper.getMainLooper());
    private LinearLayout chips;
    private LinearLayout apps;
    private Ui.Bars bars;
    private TextView total;
    private TextView today;
    private TextView empty;
    private String selected;

    private final Runnable refresh = new Runnable() {
        @Override
        public void run() {
            render();
            h.postDelayed(this, 5000L);
        }
    };

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        selected = getIntent().getStringExtra("device");

        ScrollView sc = Ui.scroll(this);
        LinearLayout body = Ui.body(sc);

        chips = Ui.row(this);
        body.addView(chips);

        LinearLayout card = Ui.card(this);
        LinearLayout top = Ui.row(this);
        LinearLayout left = Ui.col(this);
        left.addView(Ui.txt(this, "Экранное время за неделю", 12.5f, Ui.MUTED, false));
        total = Ui.txt(this, "—", 26, Ui.INK, true);
        left.addView(total);
        top.addView(left, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        today = Ui.pill(this, "сегодня —", Ui.BLUE, Ui.BLUE_SOFT);
        top.addView(today);
        card.addView(top);

        bars = new Ui.Bars(this);
        LinearLayout.LayoutParams blp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, Ui.dp(this, 148));
        blp.topMargin = Ui.dp(this, 14);
        card.addView(bars, blp);
        body.addView(card, top(14));

        body.addView(Ui.sectionTitle(this, "Топ приложений"));
        apps = Ui.col(this);
        body.addView(apps);

        setContentView(Ui.page(this,
                Ui.header(this, "АНАЛИТИКА", "Отчёты", "Экранное время и приложения"),
                sc, Ui.TAB_REPORTS));
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

    private LinearLayout.LayoutParams top(int dp) {
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        lp.topMargin = Ui.dp(this, dp);
        return lp;
    }

    private void render() {
        Db db = Db.get(this);
        List<Db.Device> devices = db.devices();

        chips.removeAllViews();
        chips.addView(chip("Все дети", selected == null, null), chipLp());
        for (Db.Device d : devices) {
            chips.addView(chip(d.name, d.id.equals(selected), d.id), chipLp());
        }

        long[] week = db.usageByDay(selected, 7);
        long sum = 0;
        for (long v : week) sum += v;

        total.setText(Ui.minutes(sum / 60000L));
        today.setText("сегодня " + Ui.minutes(week[week.length - 1] / 60000L));
        bars.set(week, weekLabels(), Ui.BLUE);

        String day = new SimpleDateFormat("yyyy-MM-dd", Locale.US).format(new Date());
        JSONArray usage = selected == null ? db.usageAll(day) : db.usage(selected, day);

        apps.removeAllViews();
        if (usage.length() == 0) {
            LinearLayout card = Ui.card(this);
            card.addView(Ui.txt(this, "Данных пока нет", 14.5f, Ui.INK, true));
            card.addView(Ui.txt(this, "Агент пришлёт статистику при первой синхронизации.",
                    12.5f, Ui.MUTED, false));
            apps.addView(card, top(12));
            return;
        }

        long max = 1;
        for (int i = 0; i < usage.length(); i++) {
            max = Math.max(max, usage.optJSONObject(i).optLong("min", 0));
        }

        LinearLayout card = Ui.card(this);
        for (int i = 0; i < usage.length() && i < 10; i++) {
            JSONObject o = usage.optJSONObject(i);
            if (o == null) continue;
            String pkg = o.optString("pkg", "?");
            long min = o.optLong("min", 0);
            int tint = Ui.tintFor(pkg);

            LinearLayout row = Ui.row(this);
            row.setPadding(0, Ui.dp(this, 8), 0, Ui.dp(this, 8));

            TextView letter = Ui.txt(this, Ui.initials(Ui.appName(pkg)),
                    14, 0xFFFFFFFF, true);
            letter.setGravity(android.view.Gravity.CENTER);
            letter.setBackground(Ui.round(this, tint, 12));
            LinearLayout.LayoutParams llp = new LinearLayout.LayoutParams(
                    Ui.dp(this, 36), Ui.dp(this, 36));
            llp.rightMargin = Ui.dp(this, 12);
            row.addView(letter, llp);

            LinearLayout col = Ui.col(this);
            col.addView(Ui.txt(this, Ui.appName(pkg), 14, Ui.INK, false));
            Ui.Progress bar = new Ui.Progress(this);
            bar.set(max == 0 ? 0 : min / (float) max, tint);
            LinearLayout.LayoutParams blp = new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, Ui.dp(this, 5));
            blp.topMargin = Ui.dp(this, 7);
            col.addView(bar, blp);
            row.addView(col, new LinearLayout.LayoutParams(0,
                    ViewGroup.LayoutParams.WRAP_CONTENT, 1f));

            TextView value = Ui.txt(this, Ui.minutes(min), 12.5f, Ui.INK2, true);
            value.setPadding(Ui.dp(this, 12), 0, 0, 0);
            row.addView(value);

            card.addView(row);
            if (i < Math.min(usage.length(), 10) - 1) card.addView(Ui.divider(this));
        }
        apps.addView(card, top(4));
    }

    private LinearLayout.LayoutParams chipLp() {
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        lp.rightMargin = Ui.dp(this, 8);
        return lp;
    }

    private TextView chip(String label, boolean on, final String value) {
        TextView t = Ui.txt(this, label, 12.5f, on ? 0xFFFFFFFF : Ui.INK2, on);
        t.setPadding(Ui.dp(this, 14), Ui.dp(this, 8), Ui.dp(this, 14), Ui.dp(this, 8));
        t.setBackground(on ? Ui.round(this, Ui.BLUE, 100)
                : Ui.roundStroke(this, Ui.SURFACE, 100, 1, Ui.LINE));
        t.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                selected = value;
                render();
            }
        });
        return t;
    }

    private static String[] weekLabels() {
        String[] out = new String[7];
        Calendar cal = Calendar.getInstance();
        cal.add(Calendar.DAY_OF_MONTH, -6);
        SimpleDateFormat f = new SimpleDateFormat("EE", new Locale("ru", "RU"));
        for (int i = 0; i < 7; i++) {
            String s = f.format(cal.getTime());
            out[i] = s.length() > 0 ? s.substring(0, 1).toUpperCase() + s.substring(1) : "";
            cal.add(Calendar.DAY_OF_MONTH, 1);
        }
        return out;
    }
}
