package ru.homeguard.agent;

import android.animation.ObjectAnimator;
import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.WindowManager;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

/** Full-screen, non-dismissable overlay used for curfew and parental lock. */
public class CurfewActivity extends Activity {

    public static void show(Context c, String reason) {
        try {
            Intent i = new Intent(c, CurfewActivity.class);
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP
                    | Intent.FLAG_ACTIVITY_NO_ANIMATION);
            i.putExtra("reason", reason);
            c.startActivity(i);
        } catch (Exception ignored) {}
    }

    public static void hide(Context c) {
        try {
            c.sendBroadcast(new Intent(CurfewActivity.class.getName() + ".HIDE").setPackage(c.getPackageName()));
        } catch (Exception ignored) {}
    }

    private TextView clock;

    private final Handler h = new Handler(Looper.getMainLooper());
    private final Runnable poll = new Runnable() {
        @Override
        public void run() {
            if (!LockState.locked) {
                finishAndRemoveTask();
                return;
            }
            if (clock != null) {
                clock.setText(new SimpleDateFormat("HH:mm", Locale.US).format(new Date()));
            }
            h.postDelayed(this, 700L);
        }
    };

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON
                | WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON
                | WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED
                | WindowManager.LayoutParams.FLAG_DISMISS_KEYGUARD);

        String reason = getIntent() == null ? "" : getIntent().getStringExtra("reason");
        String title = "Экран заблокирован";
        String sub = "Родительский контроль HomeGuard";
        if ("curfew".equals(reason)) {
            title = "Время отдыха";
            sub = "Телефон вернётся в работу по расписанию";
        } else if ("daily_limit".equals(reason)) {
            title = "Лимит на сегодня исчерпан";
            sub = "Экранное время закончилось";
        } else if ("parent".equals(reason)) {
            title = "Заблокировано родителем";
            sub = "Снять блокировку можно из консоли HomeGuard";
        }

        LinearLayout root = Ui.col(this);
        root.setGravity(Gravity.CENTER);
        root.setBackground(Ui.gradient(this, 0xFF0E1420, 0xFF1B2A4A, 0, 0));

        ImageView badge = new ImageView(this);
        badge.setImageResource(R.drawable.ic_shield);
        badge.setColorFilter(0xFFFFFFFF);
        badge.setBackground(Ui.round(this, 0x1AFFFFFF, 100));
        Ui.pad(badge, this, 20, 20, 20, 20);
        LinearLayout.LayoutParams blp = new LinearLayout.LayoutParams(
                Ui.dp(this, 88), Ui.dp(this, 88));
        blp.gravity = Gravity.CENTER_HORIZONTAL;
        root.addView(badge, blp);

        TextView t = Ui.txt(this, title, 26, 0xFFFFFFFF, true);
        t.setGravity(Gravity.CENTER);
        root.addView(t, centerTop(20));

        TextView s = Ui.txt(this, sub, 14, 0x99A8C0, false);
        s.setGravity(Gravity.CENTER);
        root.addView(s, centerTop(8));

        clock = Ui.txt(this, new SimpleDateFormat("HH:mm", Locale.US).format(new Date()),
                56, 0xFFFFFFFF, true);
        clock.setGravity(Gravity.CENTER);
        root.addView(clock, centerTop(26));

        TextView hint = Ui.txt(this, "Позвонить можно всегда — через SOS", 12.5f,
                0x6F86A6, false);
        hint.setGravity(Gravity.CENTER);
        root.addView(hint, centerTop(4));

        LinearLayout sosWrap = Ui.col(this);
        sosWrap.setGravity(Gravity.CENTER_HORIZONTAL);
        sosWrap.addView(sosButton(), new LinearLayout.LayoutParams(
                Ui.dp(this, 220), ViewGroup.LayoutParams.WRAP_CONTENT));
        root.addView(sosWrap, centerTop(30));

        setContentView(root);

        try {
            ObjectAnimator a = ObjectAnimator.ofFloat(badge, View.ALPHA, 0.6f, 1f);
            a.setDuration(1800);
            a.setRepeatCount(ObjectAnimator.INFINITE);
            a.setRepeatMode(ObjectAnimator.REVERSE);
            a.start();
        } catch (Exception ignored) {}
    }

    private View sosButton() {
        return Ui.soft(this, "SOS родителю", 0xFFFF9C9C, new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                SyncService.sos(CurfewActivity.this);
                Ui.toast(CurfewActivity.this, "SOS отправлен родителю");
            }
        });
    }

    private LinearLayout.LayoutParams centerTop(int topDp) {
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        p.gravity = Gravity.CENTER_HORIZONTAL;
        p.topMargin = Ui.dp(this, topDp);
        return p;
    }

    @Override
    protected void onResume() {
        super.onResume();
        h.removeCallbacks(poll);
        h.post(poll);
        if (Admin.isOwner(this)) {
            try {
                startLockTask();
            } catch (Exception ignored) {}
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        h.removeCallbacks(poll);
    }

    @Override
    public void onBackPressed() {
        // Swallow: leaving is only possible through a parent command.
    }

    @Override
    protected void onDestroy() {
        h.removeCallbacks(poll);
        super.onDestroy();
    }
}
