package ru.homeguard.console;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.res.ColorStateList;
import android.graphics.Canvas;
import android.graphics.Color;
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
import android.widget.Switch;
import android.widget.TextView;
import android.widget.Toast;

/**
 * Hand-rolled design system: no AndroidX, so the APK stays around 100 KB.
 * Light theme, soft gradients, rounded cards and hand-drawn charts.
 */
public final class Ui {

    public interface OnBool {
        void on(boolean value);
    }

    // ---------- palette ----------
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

    public static final int TAB_HOME = 0;
    public static final int TAB_EVENTS = 1;
    public static final int TAB_REPORTS = 2;
    public static final int TAB_SETTINGS = 3;

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

    public static Typeface bold() {
        return Typeface.create("sans-serif", Typeface.BOLD);
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

    public static TextView h1(Context c, String text) {
        return tv(c, text, 26, INK, medium());
    }

    public static TextView h2(Context c, String text) {
        return tv(c, text, 18, INK, medium());
    }

    public static TextView body(Context c, String text) {
        return tv(c, text, 14, INK2, null);
    }

    public static TextView small(Context c, String text) {
        return tv(c, text, 12, MUTED, null);
    }

    public static TextView value(Context c, String text) {
        return tv(c, text, 24, INK, medium());
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
        body.setClipChildren(false);
        pad(body, c, 16, 8, 16, 28);
        sc.addView(body, new ScrollView.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT));
        return sc;
    }

    public static LinearLayout body(ScrollView sc) {
        return (LinearLayout) sc.getChildAt(0);
    }

    public static void add(Context c, LinearLayout parent, View v, float topDp) {
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        lp.topMargin = dp(c, topDp);
        parent.addView(v, lp);
    }

    public static View space(Context c, float heightDp) {
        View v = new View(c);
        v.setLayoutParams(new LinearLayout.LayoutParams(1, dp(c, heightDp)));
        return v;
    }

    public static LinearLayout card(Context c) {
        LinearLayout l = col(c);
        pad(l, c, 16, 16, 16, 16);
        l.setBackground(round(c, SURFACE, 20));
        l.setElevation(dp(c, 2));
        l.setLayoutParams(new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        return l;
    }

    public static LinearLayout glassCard(Context c) {
        LinearLayout l = col(c);
        pad(l, c, 16, 14, 16, 14);
        l.setBackground(round(c, 0x1FFFFFFF, 18));
        l.setLayoutParams(new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        return l;
    }

    public static View divider(Context c) {
        View v = new View(c);
        v.setBackgroundColor(LINE);
        v.setLayoutParams(new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 1));
        return v;
    }

    // ---------- header ----------

    public static LinearLayout header(Activity a, String kicker, String title, String subtitle) {
        return header(a, kicker, title, subtitle, null, false);
    }

    public static LinearLayout header(Activity a, String kicker, String title, String subtitle,
                                      View extra) {
        return header(a, kicker, title, subtitle, extra, false);
    }

    public static LinearLayout headerBack(Activity a, String title, String subtitle) {
        return header(a, null, title, subtitle, null, true);
    }

    private static LinearLayout header(Activity a, String kicker, String title, String subtitle,
                                       View extra, boolean back) {
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
        pad(content, a, 20, 14, 20, 20);

        if (back) {
            LinearLayout top = row(a);
            ImageView iv = new ImageView(a);
            iv.setImageResource(R.drawable.ic_back);
            iv.setColorFilter(0xFFFFFFFF);
            LinearLayout hit = row(a);
            pad(hit, a, 0, 6, 10, 6);
            hit.addView(iv, new LinearLayout.LayoutParams(dp(a, 22), dp(a, 22)));
            hit.setOnClickListener(new View.OnClickListener() {
                @Override
                public void onClick(View v) {
                    ((Activity) v.getContext()).finish();
                }
            });
            top.addView(hit);
            content.addView(top);
        }

        if (kicker != null) {
            TextView k = tv(a, kicker, 11, 0xCCFFFFFF, medium());
            k.setLetterSpacing(0.14f);
            pad(k, a, 0, back ? 4 : 6, 0, 6);
            content.addView(k);
        }

        TextView t = tv(a, title, 26, 0xFFFFFFFF, medium());
        content.addView(t);

        if (subtitle != null) {
            TextView s = tv(a, subtitle, 13.5f, 0xCCFFFFFF, null);
            pad(s, a, 0, 5, 0, 0);
            content.addView(s);
        }

        if (extra != null) add(a, content, extra, 14);

        LinearLayout wrapper = col(a);
        wrapper.addView(content, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        frame.addView(wrapper, new FrameLayout.LayoutParams(
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
            b.setBackground(ripple(c, gradient(c, grad[0], grad[1], 16, 16), alpha(rippleColor, 0x44)));
        }
        b.setLayoutParams(new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        b.setOnClickListener(l);
        return b;
    }

    public static LinearLayout actionTile(Context c, int icon, String label,
                                          int tint, View.OnClickListener l) {
        LinearLayout box = col(c);
        box.setGravity(Gravity.CENTER_HORIZONTAL);
        box.setBackground(ripple(c, round(c, SURFACE, 18), 0x224C6FFF));
        box.setElevation(dp(c, 2));
        pad(box, c, 8, 14, 8, 12);

        LinearLayout bubble = col(c);
        bubble.setGravity(Gravity.CENTER);
        bubble.setBackground(round(c, alpha(tint, 0x18), 100));
        ImageView iv = new ImageView(c);
        iv.setImageResource(icon);
        iv.setColorFilter(tint);
        bubble.addView(iv, new LinearLayout.LayoutParams(dp(c, 22), dp(c, 22)));
        box.addView(bubble, new LinearLayout.LayoutParams(dp(c, 40), dp(c, 40)));

        TextView t = tv(c, label, 11.5f, INK2, medium());
        t.setGravity(Gravity.CENTER);
        pad(t, c, 0, 8, 0, 0);
        box.addView(t);

        box.setOnClickListener(l);
        return box;
    }

    public static LinearLayout tiles(Context c, View... items) {
        LinearLayout r = row(c);
        for (int i = 0; i < items.length; i++) {
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0,
                    ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
            if (i > 0) lp.leftMargin = dp(c, 10);
            r.addView(items[i], lp);
        }
        return r;
    }

    public static LinearLayout switchRow(Context c, String title, String sub,
                                         boolean checked, final OnBool cb) {
        LinearLayout r = row(c);
        pad(r, c, 0, 12, 0, 12);

        LinearLayout txt = col(c);
        TextView t = tv(c, title, 14.5f, INK, null);
        txt.addView(t);
        if (sub != null) {
            TextView s = tv(c, sub, 12, MUTED, null);
            pad(s, c, 0, 3, 0, 0);
            txt.addView(s);
        }
        r.addView(txt, new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f));

        Switch sw = new Switch(c);
        sw.setChecked(checked);
        sw.setThumbTintList(ColorStateList.valueOf(0xFFFFFFFF));
        sw.setTrackTintList(new ColorStateList(
                new int[][]{{android.R.attr.state_checked}, {}},
                new int[]{BLUE, 0xFFD7DEEA}));
        sw.setOnCheckedChangeListener(new android.widget.CompoundButton.OnCheckedChangeListener() {
            @Override
            public void onCheckedChanged(android.widget.CompoundButton b, boolean v) {
                cb.on(v);
            }
        });
        r.addView(sw);
        return r;
    }

    public static LinearLayout rowItem(Context c, int icon, String title, String sub,
                                       int tint, View.OnClickListener l) {
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
        LinearLayout txt = col(c);
        txt.addView(tv(c, title, 14.5f, INK, null));
        if (sub != null) {
            TextView s = tv(c, sub, 12, MUTED, null);
            pad(s, c, 0, 3, 0, 0);
            txt.addView(s);
        }
        r.addView(txt, new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        TextView chev = tv(c, "›", 22, MUTED, null);
        r.addView(chev);
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
        e.setTextSize(14.5f);
        e.setTextColor(INK);
        e.setHintTextColor(MUTED);
        e.setBackground(round(c, 0xFFF7F9FE, 14));
        e.setPadding(dp(c, 14), dp(c, 13), dp(c, 14), dp(c, 13));
        e.setLayoutParams(new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        return e;
    }

    // ---------- charts ----------

    /** Rounded linear progress bar. */
    public static final class Progress extends View {
        private float percent;
        private int color = BLUE;

        public Progress(Context c) {
            super(c);
        }

        public void set(float p, int c) {
            percent = Math.max(0f, Math.min(1f, p));
            color = c;
            invalidate();
        }

        @Override
        protected void onDraw(Canvas cv) {
            float h = getHeight();
            float r = h / 2f;
            Paint p = new Paint(Paint.ANTI_ALIAS_FLAG);
            p.setColor(0xFFE9EEF8);
            cv.drawRoundRect(new RectF(0, 0, getWidth(), h), r, r, p);
            if (percent > 0) {
                p.setColor(color);
                cv.drawRoundRect(new RectF(0, 0, Math.max(h, getWidth() * percent), h), r, r, p);
            }
        }
    }

    /** Donut chart with the value in the middle. */
    public static final class Ring extends View {
        private float percent;
        private int color = BLUE;
        private String big = "";
        private String small = "";

        public Ring(Context c) {
            super(c);
        }

        public void set(float p, int c, String bigText, String smallText) {
            percent = Math.max(0f, Math.min(1f, p));
            color = c;
            big = bigText == null ? "" : bigText;
            small = smallText == null ? "" : smallText;
            invalidate();
        }

        @Override
        protected void onDraw(Canvas cv) {
            float size = Math.min(getWidth(), getHeight());
            float stroke = size * 0.105f;
            RectF box = new RectF(stroke / 2f, stroke / 2f, size - stroke / 2f, size - stroke / 2f);
            Paint p = new Paint(Paint.ANTI_ALIAS_FLAG);
            p.setStyle(Paint.Style.STROKE);
            p.setStrokeWidth(stroke);
            p.setStrokeCap(Paint.Cap.ROUND);
            p.setColor(0xFFE9EEF8);
            cv.drawArc(box, 0, 360, false, p);
            if (percent > 0) {
                p.setColor(color);
                cv.drawArc(box, -90, 360 * percent, false, p);
            }
            Paint t = new Paint(Paint.ANTI_ALIAS_FLAG);
            t.setColor(INK);
            t.setTextAlign(Paint.Align.CENTER);
            t.setTypeface(medium());
            t.setTextSize(size * 0.20f);
            float cy = size / 2f;
            if (!small.isEmpty()) cy -= size * 0.03f;
            cv.drawText(big, size / 2f, cy + t.getTextSize() * 0.35f, t);
            if (!small.isEmpty()) {
                t.setColor(MUTED);
                t.setTypeface(null);
                t.setTextSize(size * 0.095f);
                cv.drawText(small, size / 2f, size / 2f + size * 0.20f, t);
            }
        }
    }

    /** Seven bars: oldest day first, today is highlighted. */
    public static final class Bars extends View {
        private long[] data = new long[0];
        private String[] labels = new String[0];
        private int color = BLUE;

        public Bars(Context c) {
            super(c);
        }

        public void set(long[] values, String[] names, int tint) {
            data = values == null ? new long[0] : values;
            labels = names == null ? new String[0] : names;
            color = tint;
            invalidate();
        }

        @Override
        protected void onDraw(Canvas cv) {
            if (data.length == 0) return;
            Context c = getContext();
            float labelH = sp(c, 13) + dp(c, 6);
            float chartH = getHeight() - labelH;
            long max = 1;
            for (long v : data) max = Math.max(max, v);

            float slot = getWidth() / (float) data.length;
            float bw = Math.min(dp(c, 24), slot * 0.56f);
            Paint p = new Paint(Paint.ANTI_ALIAS_FLAG);
            Paint t = new Paint(Paint.ANTI_ALIAS_FLAG);
            t.setTextAlign(Paint.Align.CENTER);
            t.setTextSize(sp(c, 10.5f));

            for (int i = 0; i < data.length; i++) {
                float bh = data[i] <= 0 ? dp(c, 3) : Math.max(dp(c, 6),
                        (chartH - dp(c, 6)) * data[i] / (float) max);
                float left = i * slot + (slot - bw) / 2f;
                float top = chartH - bh;
                p.setColor(i == data.length - 1 ? color : 0xFFDDE4F5);
                cv.drawRoundRect(new RectF(left, top, left + bw, chartH), bw / 2f, bw / 2f, p);

                t.setColor(i == data.length - 1 ? INK : MUTED);
                t.setTypeface(i == data.length - 1 ? medium() : null);
                if (i < labels.length) {
                    cv.drawText(labels[i], left + bw / 2f, chartH + sp(c, 13) + dp(c, 2), t);
                }
            }
        }
    }

    // ---------- app helpers ----------

    public static String appName(String pkg) {
        if (pkg == null) return "?";
        switch (pkg) {
            case "com.instagram.android": return "Instagram";
            case "com.google.android.youtube": return "YouTube";
            case "com.google.android.apps.youtube.music": return "YouTube Music";
            case "com.whatsapp": return "WhatsApp";
            case "org.telegram.messenger": return "Telegram";
            case "com.android.chrome": return "Chrome";
            case "com.zhiliaoapp.musically": return "TikTok";
            case "com.spotify.music": return "Spotify";
            case "com.vkontakte.android": return "VK";
            case "com.google.android.gm": return "Gmail";
            case "com.android.vending": return "Play Маркет";
            case "com.google.android.apps.photos": return "Google Фото";
            case "com.miui.gallery": return "Галерея";
            case "com.android.camera": return "Камера";
            case "com.google.android.dialer": return "Телефон";
            case "com.android.settings": return "Настройки";
            default:
                int dot = pkg.lastIndexOf('.');
                String last = dot >= 0 ? pkg.substring(dot + 1) : pkg;
                if (last.length() > 0) {
                    last = last.substring(0, 1).toUpperCase() + last.substring(1);
                }
                return last;
        }
    }

    public static int tintFor(String seed) {
        int[] palette = {BLUE, VIOLET, ORANGE, GREEN, 0xFF0EA5E9, 0xFFEC4899};
        int h = seed == null ? 0 : seed.hashCode();
        return palette[Math.abs(h) % palette.length];
    }

    public static String initials(String name) {
        if (name == null || name.trim().isEmpty()) return "?";
        String[] parts = name.trim().split("\\s+");
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < parts.length && i < 2; i++) {
            if (!parts[i].isEmpty()) {
                sb.append(parts[i].substring(0, 1).toUpperCase());
            }
        }
        return sb.toString();
    }

    public static View avatar(Context c, String name, int sizeDp) {
        TextView t = tv(c, initials(name), sizeDp * 0.38f, 0xFFFFFFFF, medium());
        t.setGravity(Gravity.CENTER);
        t.setBackground(round(c, tintFor(name), sizeDp / 2f));
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(dp(c, sizeDp), dp(c, sizeDp));
        t.setLayoutParams(lp);
        return t;
    }

    public static String minutes(long min) {
        if (min <= 0) return "нет";
        long h = min / 60;
        long m = min % 60;
        if (h == 0) return m + " мин";
        return m == 0 ? h + " ч" : h + " ч " + m + " м";
    }

    // ---------- navigation ----------

    public static LinearLayout page(Activity a, View header, View content, int tab) {
        LinearLayout main = col(a);
        main.setBackgroundColor(BG);
        if (header != null) {
            main.addView(header, new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        }
        main.addView(content, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));
        if (tab >= 0) {
            main.addView(bottomNav(a, tab), new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, dp(a, 64)));
        }
        return main;
    }

    private static View bottomNav(final Activity a, int selected) {
        String[] labels = {"Главная", "События", "Отчёты", "Настройки"};
        int[] icons = {R.drawable.ic_home, R.drawable.ic_bell,
                R.drawable.ic_chart, R.drawable.ic_settings};
        Class<?>[] targets = {MainActivity.class, EventsActivity.class,
                ReportsActivity.class, SettingsActivity.class};

        LinearLayout bar = row(a);
        bar.setBackgroundColor(SURFACE);
        bar.setElevation(dp(a, 14));
        pad(bar, a, 6, 8, 6, 10);

        for (int i = 0; i < labels.length; i++) {
            LinearLayout item = col(a);
            item.setGravity(Gravity.CENTER_HORIZONTAL);
            boolean on = i == selected;

            ImageView iv = new ImageView(a);
            iv.setImageResource(icons[i]);
            iv.setColorFilter(on ? BLUE : MUTED);
            item.addView(iv, new LinearLayout.LayoutParams(dp(a, 23), dp(a, 23)));

            TextView t = tv(a, labels[i], 10.5f, on ? BLUE : MUTED, on ? medium() : null);
            pad(t, a, 0, 4, 0, 0);
            item.addView(t);

            if (!on) {
                final Class<?> target = targets[i];
                item.setBackground(rippleMask(0x114C6FFF));
                item.setOnClickListener(new View.OnClickListener() {
                    @Override
                    public void onClick(View v) {
                        Intent it = new Intent(a, target);
                        it.addFlags(Intent.FLAG_ACTIVITY_REORDER_TO_FRONT
                                | Intent.FLAG_ACTIVITY_NO_ANIMATION);
                        a.startActivity(it);
                        a.overridePendingTransition(0, 0);
                    }
                });
            }
            bar.addView(item, new LinearLayout.LayoutParams(0,
                    ViewGroup.LayoutParams.MATCH_PARENT, 1f));
        }
        return bar;
    }

    public static void toast(Context c, String s) {
        Toast.makeText(c, s, Toast.LENGTH_SHORT).show();
    }

    public static void copy(Context c, String text) {
        android.content.ClipboardManager cm =
                (android.content.ClipboardManager) c.getSystemService(Context.CLIPBOARD_SERVICE);
        if (cm != null) {
            cm.setPrimaryClip(android.content.ClipData.newPlainText("homeguard", text));
        }
    }
}
