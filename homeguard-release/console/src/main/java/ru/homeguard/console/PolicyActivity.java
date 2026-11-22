package ru.homeguard.console;

import android.app.Activity;
import android.os.Bundle;
import android.view.View;
import android.view.ViewGroup;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;

import org.json.JSONArray;
import org.json.JSONObject;

/** Policy editor: screen time, apps, device restrictions, kiosk. */
public class PolicyActivity extends Activity {

    private String deviceId;
    private JSONObject policy;
    private EditText blocked;
    private EditText limit;
    private EditText curfew;
    private EditText kioskPkgs;

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        deviceId = getIntent().getStringExtra("device");
        Db.Device d = Db.get(this).device(deviceId);
        if (d == null) {
            finish();
            return;
        }
        policy = d.policy;

        ScrollView sc = Ui.scroll(this);
        LinearLayout body = Ui.body(sc);

        // ---- screen time ----
        body.addView(Ui.sectionTitle(this, "Экранное время"));
        LinearLayout time = Ui.card(this);
        time.addView(Ui.txt(this, "Дневной лимит", 14, Ui.INK, true));
        time.addView(Ui.txt(this, "Минуты в день, 0 — без лимита", 12, Ui.MUTED, false));
        limit = Ui.edit(this, "180", String.valueOf(policy.optInt("daily_limit_min", 0)));
        time.addView(limit, top(8));
        time.addView(Ui.txt(this, "Тихие часы", 14, Ui.INK, true), top(14));
        time.addView(Ui.txt(this, "дни (0=вс…6=сб или all) ЧЧ:ММ-ЧЧ:ММ\n"
                + "например: 1,2,3,4,5 21:30-07:00", 12, Ui.MUTED, false));
        curfew = Ui.edit(this, "1,2,3,4,5 21:30-07:00",
                curfewToText(policy.optJSONArray("curfew")));
        curfew.setMinLines(2);
        time.addView(curfew, top(8));
        body.addView(time, top(8));

        // ---- apps ----
        body.addView(Ui.sectionTitle(this, "Приложения"));
        LinearLayout apps = Ui.card(this);
        apps.addView(Ui.txt(this, "Заблокированные пакеты", 14, Ui.INK, true));
        apps.addView(Ui.txt(this, "По одному в строке: com.instagram.android", 12, Ui.MUTED, false));
        blocked = Ui.edit(this, "com.instagram.android", joinList(policy.optJSONArray("blocked")));
        blocked.setMinLines(3);
        apps.addView(blocked, top(8));
        apps.addView(Ui.divider(this), top(12));
        apps.addView(toggle("Установка приложений", null, "install_apps"));
        apps.addView(Ui.divider(this));
        apps.addView(toggle("Из неизвестных источников", null, "install_unknown"));
        apps.addView(Ui.divider(this));
        apps.addView(toggle("Удаление приложений", null, "uninstall_apps"));
        apps.addView(Ui.divider(this));
        apps.addView(toggle("Управление в настройках", null, "apps_control"));
        apps.addView(Ui.divider(this));
        apps.addView(toggle("Скрывать заблокированные", "из меню приложений", "hidden_blocked"));
        body.addView(apps, top(8));

        // ---- device ----
        body.addView(Ui.sectionTitle(this, "Устройство"));
        LinearLayout dev = Ui.card(this);
        dev.addView(toggle("Камера", null, "camera"));
        dev.addView(Ui.divider(this));
        dev.addView(toggle("Смена Wi-Fi сетей", null, "wifi_config"));
        dev.addView(Ui.divider(this));
        dev.addView(toggle("Bluetooth", null, "bluetooth"));
        dev.addView(Ui.divider(this));
        dev.addView(toggle("USB-передача файлов", null, "usb"));
        dev.addView(Ui.divider(this));
        dev.addView(toggle("Скриншоты и запись экрана", null, "screen_capture"));
        dev.addView(Ui.divider(this));
        dev.addView(toggle("Строка состояния", null, "status_bar"));
        dev.addView(Ui.divider(this));
        dev.addView(toggle("Экран блокировки", null, "keyguard"));
        body.addView(dev, top(8));

        // ---- hardening ----
        body.addView(Ui.sectionTitle(this, "Защита от обхода"));
        LinearLayout hard = Ui.card(this);
        hard.addView(toggle("Безопасный режим", "запрещён", "safe_boot"));
        hard.addView(Ui.divider(this));
        hard.addView(toggle("Сброс к заводским настройкам", "запрещён", "factory_reset"));
        hard.addView(Ui.divider(this));
        hard.addView(toggle("Отладка по USB", null, "debug"));
        hard.addView(Ui.divider(this));
        hard.addView(toggle("Добавление пользователей", null, "add_user"));
        body.addView(hard, top(8));

        // ---- kiosk ----
        body.addView(Ui.sectionTitle(this, "Киоск-режим"));
        LinearLayout kioskCard = Ui.card(this);
        kioskCard.addView(toggle("Киоск включён", "телефон только для учёбы", "kiosk_enabled"));
        kioskCard.addView(Ui.txt(this, "Разрешённые пакеты (лаунчер добавляется сам)",
                12, Ui.MUTED, false), top(8));
        JSONObject kiosk = policy.optJSONObject("kiosk");
        kioskPkgs = Ui.edit(this, "com.android.chrome",
                joinList(kiosk == null ? null : kiosk.optJSONArray("packages")));
        kioskPkgs.setMinLines(2);
        kioskCard.addView(kioskPkgs, top(8));
        body.addView(kioskCard, top(8));

        body.addView(Ui.primary(this, "Сохранить правила", new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                save();
            }
        }), top(20));
        body.addView(Ui.ghost(this, "Отмена", new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                finish();
            }
        }), top(10));

        setContentView(Ui.page(this,
                Ui.headerBack(this, "Правила", "применяются при следующей синхронизации"),
                sc, -1));
    }

    private LinearLayout.LayoutParams top(int dp) {
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        lp.topMargin = Ui.dp(this, dp);
        return lp;
    }

    private View toggle(String label, String sub, final String key) {
        boolean cur;
        if ("kiosk_enabled".equals(key)) {
            JSONObject k = policy.optJSONObject("kiosk");
            cur = k != null && k.optBoolean("enabled", false);
        } else {
            cur = policy.optBoolean(key, true);
        }
        return Ui.switchRow(this, label, sub, cur, new Ui.OnBool() {
            @Override
            public void on(boolean value) {
                try {
                    if ("kiosk_enabled".equals(key)) {
                        JSONObject k = policy.optJSONObject("kiosk");
                        if (k == null) k = new JSONObject();
                        k.put("enabled", value);
                        policy.put("kiosk", k);
                    } else {
                        policy.put(key, value);
                    }
                } catch (Exception ignored) {}
            }
        });
    }

    private void save() {
        try {
            policy.put("blocked", parseList(blocked.getText().toString()));
            int lim = 0;
            try {
                lim = Integer.parseInt(limit.getText().toString().trim());
            } catch (Exception ignored) {}
            policy.put("daily_limit_min", Math.max(0, lim));
            policy.put("curfew", parseCurfew(curfew.getText().toString()));

            JSONObject k = policy.optJSONObject("kiosk");
            if (k == null) k = new JSONObject();
            k.put("packages", parseList(kioskPkgs.getText().toString()));
            policy.put("kiosk", k);

            Db.Device d = Db.get(this).device(deviceId);
            int base = Math.max(d == null ? 0 : d.policyV, policy.optInt("v", 1));
            int next = base + 1;
            policy.put("v", next);
            Db.get(this).savePolicy(deviceId, policy);
            Ui.toast(this, "Сохранено: v" + next);
            finish();
        } catch (Exception e) {
            Ui.toast(this, "Ошибка: " + e.getMessage());
        }
    }

    private static JSONArray parseList(String raw) {
        JSONArray a = new JSONArray();
        for (String s : raw.split("[,\\s]+")) {
            String p = s.trim();
            if (p.contains(".") && !p.equals("com")) a.put(p);
        }
        return a;
    }

    private static String joinList(JSONArray a) {
        if (a == null) return "";
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < a.length(); i++) {
            if (sb.length() > 0) sb.append('\n');
            sb.append(a.optString(i, ""));
        }
        return sb.toString();
    }

    private static JSONArray parseCurfew(String raw) {
        JSONArray out = new JSONArray();
        for (String line : raw.split("\\n")) {
            line = line.trim();
            if (line.isEmpty()) continue;
            String[] parts = line.split("\\s+");
            if (parts.length < 2) continue;
            String[] tr = parts[1].split("-");
            if (tr.length != 2) continue;
            try {
                JSONObject w = new JSONObject();
                JSONArray days = new JSONArray();
                if (!parts[0].equalsIgnoreCase("all")) {
                    for (String d : parts[0].split(",")) days.put(Integer.parseInt(d.trim()));
                }
                w.put("days", days);
                w.put("from", tr[0].trim());
                w.put("to", tr[1].trim());
                out.put(w);
            } catch (Exception ignored) {}
        }
        return out;
    }

    private static String curfewToText(JSONArray arr) {
        if (arr == null) return "";
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < arr.length(); i++) {
            JSONObject w = arr.optJSONObject(i);
            if (w == null) continue;
            if (sb.length() > 0) sb.append('\n');
            JSONArray days = w.optJSONArray("days");
            if (days == null || days.length() == 0) sb.append("all");
            else {
                for (int j = 0; j < days.length(); j++) {
                    if (j > 0) sb.append(',');
                    sb.append(days.optInt(j));
                }
            }
            sb.append(' ').append(w.optString("from", "21:00"))
                    .append('-').append(w.optString("to", "07:00"));
        }
        return sb.toString();
    }
}
