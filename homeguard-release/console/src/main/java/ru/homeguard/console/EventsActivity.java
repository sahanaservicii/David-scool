package ru.homeguard.console;

import android.app.Activity;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;

import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/** Tab 2: what happened on the children's phones. */
public class EventsActivity extends Activity {

    private final Handler h = new Handler(Looper.getMainLooper());
    private LinearLayout list;

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
        ScrollView sc = Ui.scroll(this);
        LinearLayout body = Ui.body(sc);
        list = Ui.col(this);
        body.addView(list);

        setContentView(Ui.page(this,
                Ui.header(this, "ЛЕНТА", "События", "Блокировки, SOS и обновления правил"),
                sc, Ui.TAB_EVENTS));
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

    private void render() {
        Db db = Db.get(this);
        Map<String, String> names = new HashMap<>();
        for (Db.Device d : db.devices()) names.put(d.id, d.name);

        List<String[]> events = db.events(null, 100);
        list.removeAllViews();

        if (events.isEmpty()) {
            list.addView(emptyCard());
            return;
        }

        String lastDay = null;
        for (String[] e : events) {
            long ts = 0;
            try {
                ts = Long.parseLong(e[3]);
            } catch (Exception ignored) {}
            String day = dayKey(ts);
            if (!day.equals(lastDay)) {
                list.addView(Ui.sectionTitle(this, dayLabel(ts)));
                lastDay = day;
            }
            list.addView(row(e, names.get(e[0])));
        }
    }

    private View row(String[] e, String device) {
        String kind = e[1] == null ? "" : e[1];
        String text = e[2] == null ? "" : e[2];

        int icon = R.drawable.ic_info;
        int tint = Ui.BLUE;
        String title = text;

        if ("sos".equals(kind)) {
            icon = R.drawable.ic_sos;
            tint = Ui.RED;
            title = "SOS от ребёнка";
        } else if ("lock".equals(kind)) {
            icon = R.drawable.ic_lock;
            tint = Ui.ORANGE;
            title = "Экран заблокирован" + reason(text);
        } else if ("unlock".equals(kind)) {
            icon = R.drawable.ic_lock;
            tint = Ui.GREEN;
            title = "Экран разблокирован" + ("parent".equals(text) ? " родителем" : "");
        } else if ("blocked".equals(kind)) {
            icon = R.drawable.ic_apps;
            tint = Ui.VIOLET;
            title = "Попытка открыть " + Ui.appName(text);
        } else if ("policy".equals(kind)) {
            icon = R.drawable.ic_shield;
            tint = Ui.BLUE;
            title = "Правила обновлены";
        } else if ("command_failed".equals(kind)) {
            icon = R.drawable.ic_warning;
            tint = Ui.RED;
            title = "Команда не выполнена";
        }

        LinearLayout card = Ui.card(this);
        LinearLayout r = Ui.row(this);

        LinearLayout bubble = Ui.col(this);
        bubble.setGravity(android.view.Gravity.CENTER);
        bubble.setBackground(Ui.round(this, Ui.alpha(tint, 0x16), 100));
        ImageView iv = new ImageView(this);
        iv.setImageResource(icon);
        iv.setColorFilter(tint);
        bubble.addView(iv, new LinearLayout.LayoutParams(Ui.dp(this, 18), Ui.dp(this, 18)));
        LinearLayout.LayoutParams blp = new LinearLayout.LayoutParams(Ui.dp(this, 38), Ui.dp(this, 38));
        blp.rightMargin = Ui.dp(this, 12);
        r.addView(bubble, blp);

        LinearLayout col = Ui.col(this);
        col.addView(Ui.txt(this, title, 14, Ui.INK, false));
        String sub = (device == null ? "устройство" : device) + " · " + time(ts(e));
        col.addView(Ui.txt(this, sub, 11.5f, Ui.MUTED, false));
        r.addView(col, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));

        card.addView(r);
        return card;
    }

    private static long ts(String[] e) {
        try {
            return Long.parseLong(e[3]);
        } catch (Exception ex) {
            return 0;
        }
    }

    private static String reason(String r) {
        if ("curfew".equals(r)) return " · тихий час";
        if ("daily".equals(r)) return " · дневной лимит";
        if ("parent".equals(r)) return " · родитель";
        return "";
    }

    private View emptyCard() {
        LinearLayout card = Ui.card(this);
        card.setGravity(android.view.Gravity.CENTER_HORIZONTAL);
        card.setPadding(Ui.dp(this, 20), Ui.dp(this, 26), Ui.dp(this, 20), Ui.dp(this, 24));

        ImageView iv = new ImageView(this);
        iv.setImageResource(R.drawable.ic_bell);
        iv.setColorFilter(Ui.MUTED);
        card.addView(iv, new LinearLayout.LayoutParams(Ui.dp(this, 42), Ui.dp(this, 42)));

        android.widget.TextView t = Ui.txt(this, "Событий пока нет", 16, Ui.INK, true);
        t.setPadding(0, Ui.dp(this, 12), 0, 0);
        card.addView(t);

        android.widget.TextView s = Ui.txt(this,
                "Здесь появятся блокировки, попытки открыть запрещённые приложения и SOS.",
                13, Ui.MUTED, false);
        s.setGravity(android.view.Gravity.CENTER);
        s.setPadding(0, Ui.dp(this, 8), 0, 0);
        card.addView(s);
        return card;
    }

    private static String dayKey(long tsSec) {
        SimpleDateFormat f = new SimpleDateFormat("yyyyMMdd", Locale.US);
        return f.format(new Date(tsSec * 1000L));
    }

    private static String dayLabel(long tsSec) {
        SimpleDateFormat f = new SimpleDateFormat("yyyyMMdd", Locale.US);
        Calendar now = Calendar.getInstance();
        String today = f.format(now.getTime());
        now.add(Calendar.DAY_OF_MONTH, -1);
        String yesterday = f.format(now.getTime());
        String d = f.format(new Date(tsSec * 1000L));
        if (d.equals(today)) return "Сегодня";
        if (d.equals(yesterday)) return "Вчера";
        return new SimpleDateFormat("d MMMM", new Locale("ru", "RU")).format(new Date(tsSec * 1000L));
    }

    private static String time(long tsSec) {
        if (tsSec <= 0) return "?";
        return new SimpleDateFormat("HH:mm", Locale.US).format(new Date(tsSec * 1000L));
    }
}
