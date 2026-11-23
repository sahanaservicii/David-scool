package ru.homeguard.agent;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.res.ColorStateList;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.RectF;
import android.graphics.Typeface;
import android.graphics.drawable.Drawable;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.RippleDrawable;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

/**
 * Same design language as the console, trimmed for the agent: no tabs, no charts.
 * Framework widgets only, so the APK stays around 80 KB.
 */
public final class Ui {

    public static final int BG = 0xFFF4F6FB;
    public static final int SURFACE = 0xFFFFFFFF;
    public static final int INK = 0xFF111827;
    public static final int INK2 = 0xFF4B5563;
    public static final int MUTED = 0xFF8A94A6;
    public static final int LINE = 0xFFE8ECF4;
    public static final int BLUE = 0xFF4C6FFF;
    public static final int VIOLET = 0xFF8B5CF6;
    public static final int ORANGE = 0xFFFF8A4C;
    public static final int GREEN = 0xFF22C55E;
    public static final int RED = 0xFFEF4444;
    public static final int BLUE_SOFT = 0xFFEDF1FF;
    public static final int NIGHT = 0xFF0E1420;

    private Ui() {}

    // ---------- metrics ----------

    public static int dp(Context c, float v) {
        return Math.round(v * c.getResources().getDisplayMetrics().density);
    }

    public static float sp(Context c, float v) {
        return TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_SP, v,
                c.getResources().getDisplayMetrics());
    }

    public static Typeface medium() {
        return Typeface.create("sans-serif-medium", Typeface.NORMAL);
    }

    public static void pad(View v, Context c, float l, float t, float r, float b) {
        v.setPadding(dp(c, l), dp(c, t), dp(c, r), dp(c, b));
    }

    public static int alpha(int color, int a) {
        return (color & 0x00FFFFFF) | (a << 24);
    }

    // ---------- drawables ----------

    public static GradientDrawable round(Context c, int color, float radiusDp) {
        GradientDrawable g = new GradientDrawable();
        g.setColor(color);
        g.setCornerRadius(dp(c, radiusDp));
        return g;
    }

    public static GradientDrawable roundStroke(Context c, int color, float radiusDp,
                                               float strokeDp, int strokeColor) {
        GradientDrawable g = round(c, color, radiusDp);
        g.setStroke(dp(c, strokeDp), strokeColor);
        return g;
    }

    public static GradientDrawable gradient(Context c, int from, int to,
                                            float topRadiusDp, float bottomRadiusDp) {
        GradientDrawable g = new GradientDrawable(GradientDrawable.Orientation.TL_BR,
                new int[]{from, to});
        float t = dp(c, topRadiusDp);
        float b = dp(c, bottomRadiusDp);
        g.setCornerRadii(new float[]{t, t, t, t, b, b, b, b});
        return g;
    }

    public static Drawable ripple(Context c, Drawable content, int maskColor) {
        return new RippleDrawable(ColorStateList.valueOf(maskColor), content,
                content == null ? null : content);
    }

    public static Drawable rippleMask(int maskColor) {
        return new RippleDrawable(ColorStateList.valueOf(maskColor), null, null);
    }

    // ---------- text ----------

    private static TextView tv(Context c, String text, float sizeSp, int color, Typeface tf) {
        TextView t = new TextView(c);
        t.setText(text);
        t.setTextSize(sizeSp);
        t.setTextColor(color);
        if (tf != null) t.setTypeface(tf);
        t.setIncludeFontPadding(false);
        return t;
    }

    public static TextView txt(Context c, String text, float sizeSp, int color, boolean med) {
        return tv(c, text, sizeSp, color, med ? medium() : null);
    }

    public static TextView sectionTitle(Context c, String text) {
        TextView t = tv(c, text.toUpperCase(), 11.5f, MUTED, medium());
        t.setLetterSpacing(0.09f);
        pad(t, c, 4, 18, 4, 8);
        return t;
    }

    public static TextView pill(Context c, String text, int fg, int bg) {
        TextView t = tv(c, text, 11.5f, fg, medium());
        pad(t, c, 9, 4, 9, 4);
        t.setBackground(round(c, bg, 100));
        return t;
    }

    public static String minutes(long min) {
        if (min <= 0) return "0 мин";
        long h = min / 60;
        long m = min % 60;
        if (h == 0) return m + " мин";
        return m == 0 ? h + " ч" : h + " ч " + m + " м";
    }

    // ---------- layout ----------

    public static LinearLayout col(Context c) {
        LinearLayout l = new LinearLayout(c);
        l.setOrientation(LinearLayout.VERTICAL);
        l.setLayoutParams(new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        return l;
    }

    public static LinearLayout row(Context c) {
        LinearLayout l = new LinearLayout(c);
        l.setOrientation(LinearLayout.HORIZONTAL);
        l.setGravity(Gravity.CENTER_VERTICAL);
        l.setLayoutParams(new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        return l;
    }

    public static ScrollView scroll(Context c) {
        ScrollView sc = new ScrollView(c);
        sc.setFillViewport(true);
        sc.setClipToPadding(false);
        LinearLayout body = col(c);
        pad(body, c, 16, 8, 16, 28);
        sc.addView(body, new ScrollView.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT));
        return sc;
    }

    public static LinearLayout body(ScrollView sc) {
        return (LinearLayout) sc.getChildAt(0);
    }

    public static LinearLayout card(Context c) {
        LinearLayout l = col(c);
        pad(l, c, 16, 16, 16, 16);
        l.setBackground(round(c, SURFACE, 20));
        l.setElevation(dp(c, 2));
        return l;
    }

    public static LinearLayout glassCard(Context c) {
        LinearLayout l = col(c);
        pad(l, c, 16, 14, 16, 14);
        l.setBackground(round(c, 0x1FFFFFFF, 18));
        return l;
    }

    public static View divider(Context c) {
        View v = new View(c);
        v.setBackgroundColor(LINE);
        v.setLayoutParams(new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 1));
        return v;
    }

    // ---------- header ----------

    public static LinearLayout header(Activity a, String kicker, String title, String subtitle,
                                      View extra) {
        FrameLayout frame = new FrameLayout(a);
        frame.setBackground(gradient(a, BLUE, VIOLET, 0, 26));
        frame.setClipChildren(false);

        View glow = new View(a);
        GradientDrawable oval = new GradientDrawable();
        oval.setShape(GradientDrawable.OVAL);
        oval.setColor(0x1AFFFFFF);
        glow.setBackground(oval);
        FrameLayout.LayoutParams glp = new FrameLayout.LayoutParams(dp(a, 190), dp(a, 190));
        glp.gravity = Gravity.TOP | Gravity.RIGHT;
        glp.rightMargin = -dp(a, 60);
        glp.topMargin = -dp(a, 90);
        frame.addView(glow, glp);

        LinearLayout content = col(a);
        pad(content, a, 20, 18, 20, 20);

        if (kicker != null) {
            TextView k = tv(a, kicker, 11, 0xCCFFFFFF, medium());
            k.setLetterSpacing(0.14f);
            pad(k, a, 0, 0, 0, 6);
            content.addView(k);
        }

        content.addView(tv(a, title, 26, 0xFFFFFFFF, medium()));

        if (subtitle != null) {
            TextView s = tv(a, subtitle, 13.5f, 0xCCFFFFFF, null);
            pad(s, a, 0, 5, 0, 0);
            content.addView(s);
        }

        if (extra != null) {
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
            lp.topMargin = dp(a, 14);
            content.addView(extra, lp);
        }

        frame.addView(content, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        LinearLayout out = col(a);
        out.addView(frame, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        return out;
    }

    // ---------- controls ----------

    public static Button primary(Context c, String label, View.OnClickListener l) {
        return button(c, label, 0xFFFFFFFF, new int[]{BLUE, VIOLET}, BLUE, l);
    }

    public static Button ghost(Context c, String label, View.OnClickListener l) {
        Button b = button(c, label, BLUE, null, BLUE, l);
        b.setBackground(ripple(c, roundStroke(c, SURFACE, 16, 1.2f, LINE), 0x224C6FFF));
        return b;
    }

    public static Button danger(Context c, String label, View.OnClickListener l) {
        Button b = button(c, label, RED, null, RED, l);
        b.setBackground(ripple(c, round(c, 0xFFFEECEC, 16), 0x22EF4444));
        return b;
    }

    public static Button soft(Context c, String label, int color, View.OnClickListener l) {
        Button b = button(c, label, color, null, color, l);
        b.setBackground(ripple(c, round(c, alpha(color, 0x1A), 16), alpha(color, 0x33)));
        return b;
    }

    private static Button button(Context c, String label, int textColor, int[] grad,
                                 int rippleColor, View.OnClickListener l) {
        Button b = new Button(c);
        b.setText(label);
        b.setAllCaps(false);
        b.setTextSize(15);
        b.setTextColor(textColor);
        b.setTypeface(medium());
        b.setGravity(Gravity.CENTER);
        b.setMinHeight(0);
        b.setMinWidth(0);
        b.setIncludeFontPadding(false);
        b.setStateListAnimator(null);
        b.setPadding(dp(c, 18), dp(c, 15), dp(c, 18), dp(c, 15));
        if (grad != null) {
            b.setBackground(ripple(c, gradient(c, grad[0], grad[1], 16, 16),
                    alpha(rippleColor, 0x44)));
        }
        b.setLayoutParams(new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        b.setOnClickListener(l);
        return b;
    }

    public static LinearLayout rowItem(Context c, int icon, String title, String sub,
                                       int tint, String state, int stateColor,
                                       View.OnClickListener l) {
        LinearLayout r = row(c);
        pad(r, c, 0, 12, 0, 12);
        if (icon != 0) {
            LinearLayout bubble = col(c);
            bubble.setGravity(Gravity.CENTER);
            bubble.setBackground(round(c, alpha(tint, 0x16), 100));
            ImageView iv = new ImageView(c);
            iv.setImageResource(icon);
            iv.setColorFilter(tint);
            bubble.addView(iv, new LinearLayout.LayoutParams(dp(c, 18), dp(c, 18)));
            LinearLayout.LayoutParams blp = new LinearLayout.LayoutParams(dp(c, 34), dp(c, 34));
            blp.rightMargin = dp(c, 12);
            r.addView(bubble, blp);
        }
        LinearLayout text = col(c);
        text.addView(tv(c, title, 14.5f, INK, null));
        if (sub != null) {
            TextView s = tv(c, sub, 12, MUTED, null);
            pad(s, c, 0, 3, 0, 0);
            text.addView(s);
        }
        r.addView(text, new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        if (state != null) {
            TextView st = tv(c, state, 12, stateColor, medium());
            pad(st, c, 10, 0, 0, 0);
            r.addView(st);
        }
        if (l != null) {
            r.setBackground(rippleMask(0x114C6FFF));
            r.setOnClickListener(l);
        }
        return r;
    }

    public static EditText edit(Context c, String hint, String value) {
        EditText e = new EditText(c);
        e.setHint(hint);
        e.setText(value == null ? "" : value);
        e.setTextSize(14f);
        e.setTextColor(INK);
        e.setHintTextColor(MUTED);
        e.setBackground(round(c, 0xFFF7F9FE, 14));
        e.setPadding(dp(c, 14), dp(c, 13), dp(c, 14), dp(c, 13));
        e.setLayoutParams(new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        return e;
    }

    /** Rounded linear progress bar. */
    public static final class Progress extends View {
        private float percent;
        private int color = BLUE;
        private int track = 0xFFE9EEF8;

        public Progress(Context c) {
            super(c);
        }

        public void set(float p, int c) {
            set(p, c, 0xFFE9EEF8);
        }

        public void set(float p, int c, int trackColor) {
            percent = Math.max(0f, Math.min(1f, p));
            color = c;
            track = trackColor;
            invalidate();
        }

        @Override
        protected void onDraw(Canvas cv) {
            float h = getHeight();
            float r = h / 2f;
            Paint p = new Paint(Paint.ANTI_ALIAS_FLAG);
            p.setColor(track);
            cv.drawRoundRect(new RectF(0, 0, getWidth(), h), r, r, p);
            if (percent > 0) {
                p.setColor(color);
                cv.drawRoundRect(new RectF(0, 0, Math.max(h, getWidth() * percent), h), r, r, p);
            }
        }
    }

    // ---------- page ----------

    public static LinearLayout page(Activity a, View header, View content) {
        LinearLayout main = col(a);
        main.setBackgroundColor(BG);
        if (header != null) {
            main.addView(header, new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        }
        main.addView(content, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));
        return main;
    }

    public static void toast(Context c, String s) {
        Toast.makeText(c, s, Toast.LENGTH_SHORT).show();
    }

    public static void copy(Context c, String text) {
        try {
            android.content.ClipboardManager cm =
                    (android.content.ClipboardManager) c.getSystemService(Context.CLIPBOARD_SERVICE);
            if (cm != null) cm.setPrimaryClip(android.content.ClipData.newPlainText("HomeGuard", text == null ? "" : text));
        } catch (Exception ignored) {}
    }

    public static void openSettings(Activity a, String action, String pkg) {
        try {
            Intent i = new Intent(action);
            if (pkg != null) i.setData(android.net.Uri.parse("package:" + pkg));
            a.startActivity(i);
        } catch (Exception e) {
            toast(a, "Откройте настройки Android вручную");
        }
    }
}
