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

import java.util.List;

/** Live server diagnostics: connections, auth failures, sync events. Local only. */
public class DiagActivity extends Activity {

    private final Handler h = new Handler(Looper.getMainLooper());
    private LinearLayout logCard;
    private TextView summary;
    private ScrollView sc;

    private final Runnable refresh = new Runnable() {
        @Override
        public void run() {
            render();
            h.postDelayed(this, 2000L);
        }
    };

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        sc = Ui.scroll(this);
        LinearLayout body = Ui.body(sc);

        summary = Ui.txt(this, "", 13, Ui.MUTED, false);
        summary.setPadding(Ui.dp(this, 16), Ui.dp(this, 8), Ui.dp(this, 16), 0);
        body.addView(summary);

        LinearLayout actions = Ui.row(this);
        actions.setPadding(Ui.dp(this, 16), Ui.dp(this, 10), Ui.dp(this, 16), 0);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        actions.addView(Ui.ghost(this, "Копировать", new View.OnClickListener() {
            @Override public void onClick(View v) {
                Ui.copy(DiagActivity.this, ServerLog.dump());
                Ui.toast(DiagActivity.this, "Лог скопирован");
            }
        }), lp);
        LinearLayout.LayoutParams lp2 = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        lp2.leftMargin = Ui.dp(this, 10);
        actions.addView(Ui.ghost(this, "Очистить", new View.OnClickListener() {
            @Override public void onClick(View v) {
                ServerLog.clear();
                render();
            }
        }), lp2);
        body.addView(actions);

        logCard = Ui.card(this);
        LinearLayout wrap = Ui.col(this);
        wrap.setPadding(Ui.dp(this, 16), Ui.dp(this, 12), Ui.dp(this, 16), Ui.dp(this, 24));
        wrap.addView(logCard);
        body.addView(wrap);

        setContentView(Ui.page(this, Ui.headerBack(this, "Диагностика", "Подключения, ошибки, sync"), sc, -1));
    }

    @Override protected void onResume() { super.onResume(); h.post(refresh); }
    @Override protected void onPause() { super.onPause(); h.removeCallbacks(refresh); }

    private void render() {
        List<ServerLog.Entry> list = ServerLog.snapshot();
        boolean alive = ConsoleService.alive;
        summary.setText((alive ? "Сервер работает · " : "Сервер остановлен · ")
                + list.size() + " записей · порт " + ControlServer.PORT);

        logCard.removeAllViews();
        if (list.isEmpty()) {
            logCard.addView(Ui.txt(this,
                    "Пока пусто. Если агент не подключается — здесь появятся auth FAIL, "
                            + "отказы или ничего (значит запросы не доходят до консоли).",
                    13, Ui.MUTED, false));
            return;
        }
        int start = Math.max(0, list.size() - 120);
        boolean first = true;
        for (int i = list.size() - 1; i >= start; i--) {
            ServerLog.Entry e = list.get(i);
            if (!first) logCard.addView(Ui.divider(this));
            first = false;
            int color = "E".equals(e.level) ? 0xFFB91C1C : "W".equals(e.level) ? 0xFFB45309 : Ui.INK;
            TextView t = Ui.txt(this, e.line(), 12, color, false);
            t.setPadding(0, Ui.dp(this, 8), 0, Ui.dp(this, 8));
            t.setTypeface(android.graphics.Typeface.MONOSPACE);
            logCard.addView(t);
        }
    }
}
