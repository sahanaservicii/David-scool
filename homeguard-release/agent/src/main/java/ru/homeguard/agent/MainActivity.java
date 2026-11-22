package ru.homeguard.agent;

import android.Manifest;
import android.app.Activity;
import android.app.AppOpsManager;
import android.app.admin.DevicePolicyManager;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.PowerManager;
import android.os.Process;
import android.provider.Settings;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import java.util.ArrayList;
import java.util.List;

/**
 * Child-facing screen: protection status, SOS, setup checklist and pairing.
 * The checklist doubles as the first-run permissions wizard.
 */
public class MainActivity extends Activity {

    private final Handler h = new Handler(Looper.getMainLooper());

    private ScrollView scroll;
    private EditText pairField;
    private EditText nameField;
    private LinearLayout pairCard;

    private TextView heroPill;
    private TextView heroTitle;
    private TextView heroSub;
    private TextView readyLabel;
    private TextView syncValue;
    private TextView policyValue;
    private Ui.Progress readyBar;

    private LinearLayout lockBox;
    private LinearLayout checklist;
    private LinearLayout diagnostics;

    private String setupSig = "";
    private String diagSig = "";
    private String lockSig = "#";

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

        scroll = Ui.scroll(this);
        LinearLayout body = Ui.body(scroll);

        body.addView(buildHeader());

        // SOS — the one thing a child must always be able to find.
        body.addView(sosCard(), lp(0, 16));

        lockBox = Ui.col(this);
        lockBox.setVisibility(View.GONE);
        body.addView(lockBox);

        body.addView(Ui.sectionTitle(this, "Настройка"));
        LinearLayout setupCard = Ui.card(this);
        checklist = Ui.col(this);
        setupCard.addView(checklist);
        body.addView(setupCard, lp(0, 0));

        body.addView(Ui.sectionTitle(this, "Подключение"));
        pairCard = Ui.card(this);
        buildPairing(pairCard);
        body.addView(pairCard, lp(0, 0));

        body.addView(Ui.sectionTitle(this, "Диагностика"));
        LinearLayout diagCard = Ui.card(this);
        diagnostics = Ui.col(this);
        diagCard.addView(diagnostics);
        body.addView(diagCard, lp(0, 0));

        body.addView(footer(), lp(0, 22));

        setContentView(Ui.page(this, null, scroll));

        nameField.setText(Store.deviceName(this));

        WatchdogJob.schedule(this);
        SyncService.start(this);
        Scheduler.start(this);
        render();
    }

    @Override
    protected void onResume() {
        super.onResume();
        h.removeCallbacks(refresh);
        h.post(refresh);
    }

    @Override
    protected void onPause() {
        super.onPause();
        h.removeCallbacks(refresh);
    }

    // ---------------------------------------------------------------- header

    private View buildHeader() {
        LinearLayout glass = Ui.glassCard(this);

        LinearLayout pillRow = Ui.row(this);
        heroPill = Ui.pill(this, "ПРОВЕРКА…", 0xFFFFFFFF, 0x33FFFFFF);
        pillRow.addView(heroPill);
        glass.addView(pillRow);

        heroTitle = Ui.txt(this, "Защита", 19, 0xFFFFFFFF, true);
        glass.addView(heroTitle, lp(0, 10));

        heroSub = Ui.txt(this, "Связь с консолью родителя", 12.5f, 0xCCFFFFFF, false);
        glass.addView(heroSub, lp(0, 4));

        readyBar = new Ui.Progress(this);
        LinearLayout.LayoutParams blp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, Ui.dp(this, 8));
        blp.topMargin = Ui.dp(this, 14);
        glass.addView(readyBar, blp);

        readyLabel = Ui.txt(this, "", 11.5f, 0xCCFFFFFF, false);
        glass.addView(readyLabel, lp(0, 6));

        LinearLayout stats = Ui.row(this);
        LinearLayout syncCell = statCell("Обновлено", "");
        syncValue = (TextView) syncCell.getChildAt(1);
        LinearLayout policyCell = statCell("Политика", "");
        policyValue = (TextView) policyCell.getChildAt(1);
        stats.addView(syncCell, new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        stats.addView(policyCell, new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        glass.addView(stats, lp(0, 14));

        return Ui.header(this, "HOME GUARD", "Защита",
                "Телефон под присмотром родителя", glass);
    }

    private LinearLayout statCell(String label, String value) {
        LinearLayout c = Ui.col(this);
        c.addView(Ui.txt(this, label, 10.5f, 0x99FFFFFF, false));
        TextView v = Ui.txt(this, value, 13.5f, 0xFFFFFFFF, true);
        c.addView(v, lp(0, 2));
        return c;
    }

    // ------------------------------------------------------------------- SOS

    private View sosCard() {
        LinearLayout card = Ui.row(this);
        Ui.pad(card, this, 18, 18, 18, 18);
        card.setBackground(Ui.ripple(this,
                Ui.gradient(this, Ui.RED, Ui.ORANGE, 20, 20), 0x40FFFFFF));
        card.setElevation(Ui.dp(this, 3));

        ImageView icon = new ImageView(this);
        icon.setImageResource(R.drawable.ic_sos);
        icon.setColorFilter(0xFFFFFFFF);
        icon.setBackground(Ui.round(this, 0x33FFFFFF, 100));
        Ui.pad(icon, this, 9, 9, 9, 9);
        card.addView(icon, new LinearLayout.LayoutParams(Ui.dp(this, 46), Ui.dp(this, 46)));

        LinearLayout text = Ui.col(this);
        Ui.pad(text, this, 14, 0, 0, 0);
        text.addView(Ui.txt(this, "SOS родителю", 17, 0xFFFFFFFF, true));
        text.addView(Ui.txt(this, "Сигнал и координаты в консоль", 12.5f, 0xFFFFE6D8, false));
        card.addView(text, new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f));

        TextView send = Ui.txt(this, "→", 20, 0xFFFFFFFF, true);
        card.addView(send);

        card.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                sosNow();
            }
        });
        return card;
    }

    private void sosNow() {
        SyncService.sos(this);
        Ui.toast(this, "SOS отправлен родителю");
    }

    private View lockNotice() {
        LinearLayout card = Ui.card(this);
        LinearLayout r = Ui.row(this);
        ImageView icon = new ImageView(this);
        icon.setImageResource(R.drawable.ic_lock);
        icon.setColorFilter(Ui.ORANGE);
        icon.setBackground(Ui.round(this, Ui.alpha(Ui.ORANGE, 0x16), 100));
        Ui.pad(icon, this, 8, 8, 8, 8);
        r.addView(icon, new LinearLayout.LayoutParams(Ui.dp(this, 36), Ui.dp(this, 36)));

        LinearLayout t = Ui.col(this);
        Ui.pad(t, this, 12, 0, 0, 0);
        t.addView(Ui.txt(this, "Сейчас действует ограничение", 14.5f, Ui.INK, true));
        t.addView(Ui.txt(this, lockText(), 12, Ui.MUTED, false));
        r.addView(t, new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        card.addView(r);
        return card;
    }

    private String lockText() {
        String r = LockState.reason;
        if ("curfew".equals(r)) return "Время отдыха по расписанию";
        if ("daily_limit".equals(r)) return "Лимит экранного времени исчерпан";
        if ("parent".equals(r)) return "Заблокировано из консоли";
        return "Экран заблокирован";
    }

    // ---------------------------------------------------------------- setup

    private void render() {
        boolean owner = Admin.isOwner(this);
        boolean admin = Admin.isAdmin(this);
        boolean paired = Store.paired(this);
        boolean notif = granted(Manifest.permission.POST_NOTIFICATIONS);
        boolean loc = granted(Manifest.permission.ACCESS_FINE_LOCATION);
        boolean usage = usageAccess();
        boolean a11y = a11yOn();
        boolean overlay = Settings.canDrawOverlays(this);
        boolean battery = batteryFree();
        boolean adb = adbOn();

        boolean[] items = {owner || admin, paired, notif, loc, usage, a11y, overlay, battery, !adb};
        int done = 0;
        for (boolean v : items) if (v) done++;
        int total = items.length;

        long last = Store.getLong(this, "last_sync", 0);
        int pv = Store.getInt(this, "policy_v", -1);

        readyBar.set(done / (float) total, 0xFFFFFFFF, 0x33FFFFFF);
        readyLabel.setText("Готовность " + done + " из " + total);
        heroTitle.setText(done == total ? "Телефон под присмотром"
                : "Осталось шагов: " + (total - done));
        heroSub.setText(paired ? "Связь с консолью родителя"
                : "Привяжите телефон к консоли");
        if (done == total) {
            heroPill.setText("ЗАЩИТА ВКЛЮЧЕНА");
            heroPill.setTextColor(0xFFFFFFFF);
            heroPill.setBackground(Ui.round(this, 0x3322C55E, 100));
        } else if (paired) {
            heroPill.setText("НУЖНА НАСТРОЙКА");
            heroPill.setTextColor(0xFFFFFFFF);
            heroPill.setBackground(Ui.round(this, 0x33FF8A4C, 100));
        } else {
            heroPill.setText("НЕ ПРИВЯЗАН");
            heroPill.setTextColor(0xFFFFFFFF);
            heroPill.setBackground(Ui.round(this, 0x33FF8A4C, 100));
        }
        syncValue.setText(ago(last));
        policyValue.setText(pv < 0 ? "—" : "v" + pv);

        String lsig = LockState.locked + "|" + LockState.reason;
        if (!lsig.equals(lockSig)) {
            lockSig = lsig;
            lockBox.removeAllViews();
            if (LockState.locked) {
                lockBox.setVisibility(View.VISIBLE);
                lockBox.addView(lockNotice(), lp(0, 12));
            } else {
                lockBox.setVisibility(View.GONE);
            }
        }

        String sig = owner + "|" + admin + "|" + paired + "|" + notif + "|" + loc + "|"
                + usage + "|" + a11y + "|" + overlay + "|" + battery + "|" + adb
                + "|" + Store.deviceId(this) + "|" + Store.serverUrl(this);
        if (!sig.equals(setupSig)) {
            setupSig = sig;
            buildChecklist(owner, admin, paired, notif, loc, usage, a11y, overlay, battery, adb);
        }

        String dsig = last + "|" + pv + "|" + LockState.locked + "|" + LockState.reason + "|"
                + (Usage.totalMs(this) / 60000L) + "|" + LocationReporter.providerHint(this)
                + "|" + adb + "|" + Store.serverUrl(this);
        if (!dsig.equals(diagSig)) {
            diagSig = dsig;
            buildDiagnostics();
        }
    }

    private void buildChecklist(boolean owner, boolean admin, boolean paired, boolean notif,
                                boolean loc, boolean usage, boolean a11y, boolean overlay,
                                boolean battery, boolean adb) {
        checklist.removeAllViews();

        addRow(checklist, R.drawable.ic_shield, "Права владельца устройства",
                owner ? "Управление телефоном включено"
                        : admin ? "Есть только админ-права (ограничено)"
                        : "Выдаются при первичной настройке по ADB",
                owner, owner ? "Готово" : admin ? "Частично" : "Нужно",
                owner ? Ui.GREEN : admin ? Ui.ORANGE : Ui.RED,
                owner ? null : new View.OnClickListener() {
                    @Override
                    public void onClick(View v) {
                        askAdmin();
                    }
                });

        addRow(checklist, R.drawable.ic_link, "Привязка к консоли",
                paired ? Store.deviceId(MainActivity.this) : "Вставьте код из консоли ниже",
                paired, paired ? "Готово" : "Нужно", paired ? Ui.GREEN : Ui.RED,
                new View.OnClickListener() {
                    @Override
                    public void onClick(View v) {
                        scrollToPairing();
                    }
                });

        addRow(checklist, R.drawable.ic_bell, "Уведомления",
                "Служба защиты в статус-баре", notif, notif ? "Готово" : "Нужно",
                notif ? Ui.GREEN : Ui.RED, new View.OnClickListener() {
                    @Override
                    public void onClick(View v) {
                        askNotifications();
                    }
                });

        addRow(checklist, R.drawable.ic_pin, "Геолокация",
                "Местоположение и геозоны", loc, loc ? "Готово" : "Нужно",
                loc ? Ui.GREEN : Ui.RED, new View.OnClickListener() {
                    @Override
                    public void onClick(View v) {
                        askLocation();
                    }
                });

        addRow(checklist, R.drawable.ic_clock, "Статистика использования",
                "Подсчёт экранного времени", usage, usage ? "Готово" : "Нужно",
                usage ? Ui.GREEN : Ui.RED, new View.OnClickListener() {
                    @Override
                    public void onClick(View v) {
                        Ui.openSettings(MainActivity.this, Settings.ACTION_USAGE_ACCESS_SETTINGS, null);
                    }
                });

        addRow(checklist, R.drawable.ic_apps, "Специальные возможности",
                "Блокировка приложений на экране", a11y, a11y ? "Готово" : "Нужно",
                a11y ? Ui.GREEN : Ui.RED, new View.OnClickListener() {
                    @Override
                    public void onClick(View v) {
                        Ui.openSettings(MainActivity.this, Settings.ACTION_ACCESSIBILITY_SETTINGS, null);
                    }
                });

        addRow(checklist, R.drawable.ic_lock, "Поверх других приложений",
                "Экран блокировки и тихий час", overlay, overlay ? "Готово" : "Нужно",
                overlay ? Ui.GREEN : Ui.RED, new View.OnClickListener() {
                    @Override
                    public void onClick(View v) {
                        try {
                            Intent i = new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION);
                            i.setData(Uri.parse("package:" + getPackageName()));
                            startActivity(i);
                        } catch (Exception e) {
                            Ui.toast(MainActivity.this, "Настройки → Приложения → Спец. доступ");
                        }
                    }
                });

        addRow(checklist, R.drawable.ic_battery, "Батарея без ограничений",
                "Чтобы защита не засыпала", battery, battery ? "Готово" : "Нужно",
                battery ? Ui.GREEN : Ui.ORANGE, new View.OnClickListener() {
                    @Override
                    public void onClick(View v) {
                        askBattery();
                    }
                });

        addRow(checklist, R.drawable.ic_warning, "Отладка по USB (ADB)",
                adb ? "Выключите после настройки" : "Выключена — так и должно быть",
                !adb, adb ? "ВКЛ" : "Выкл", adb ? Ui.RED : Ui.GREEN,
                adb ? new View.OnClickListener() {
                    @Override
                    public void onClick(View v) {
                        Ui.openSettings(MainActivity.this,
                                Settings.ACTION_APPLICATION_DEVELOPMENT_SETTINGS, null);
                    }
                } : null);
    }

    private void addRow(LinearLayout parent, int icon, String title, String sub, boolean ok,
                        String state, int stateColor, View.OnClickListener l) {
        if (parent.getChildCount() > 0) parent.addView(Ui.divider(this));
        parent.addView(Ui.rowItem(this, icon, title, sub, ok ? Ui.GREEN : Ui.ORANGE,
                state, stateColor, l));
    }

    // ------------------------------------------------------------ diagnostics

    private void buildDiagnostics() {
        diagnostics.removeAllViews();
        diagRow("Android", Build.VERSION.RELEASE + " (SDK " + Build.VERSION.SDK_INT + ")");
        diagRow("Модель", Build.MANUFACTURER + " " + Build.MODEL);
        diagRow("ID устройства", Store.deviceId(this));
        String srv = Store.serverUrl(this);
        diagRow("Сервер", srv == null ? "не привязан"
                : srv.replace("http://", "") + (Store.servers(this).size() > 1 ? " +" : ""));
        diagRow("Гео", LocationReporter.providerHint(this));
        diagRow("Экран сегодня", Ui.minutes(Usage.totalMs(this) / 60000L));
        diagRow("Блокировка", LockState.locked ? lockText() : "нет");
        diagRow("Синхронизация", ago(Store.getLong(this, "last_sync", 0)));
    }

    private void diagRow(String label, String value) {
        LinearLayout r = Ui.row(this);
        Ui.pad(r, this, 0, 9, 0, 9);
        r.addView(Ui.txt(this, label, 13, Ui.MUTED, false),
                new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        TextView v = Ui.txt(this, value, 13, Ui.INK2, true);
        v.setGravity(Gravity.END);
        r.addView(v);
        diagnostics.addView(r);
    }

    // --------------------------------------------------------------- pairing

    private void buildPairing(LinearLayout card) {
        card.addView(Ui.txt(this, "Код привязки", 11.5f, Ui.MUTED, false));

        // Главный путь: навести камеру на QR в консоли родителя — код подставится сам.
        card.addView(Ui.primary(this, "Сканировать QR", new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                try {
                    Intent i = new Intent(MainActivity.this, ScanActivity.class);
                    startActivityForResult(i, 71);
                } catch (Exception e) {
                    Ui.toast(MainActivity.this, "Не удалось открыть камеру — введите код ниже");
                }
            }
        }), lp(0, 2));
        card.addView(Ui.txt(this, "…или введите код вручную:", 11.5f, Ui.MUTED, false), lp(0, 10));

        pairField = Ui.edit(this, "hg1:192.168.1.10+192.168.9.2:8787:kid-ab12:КОД", "");
        pairField.setInputType(InputType.TYPE_CLASS_TEXT
                | InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS | InputType.TYPE_TEXT_FLAG_MULTI_LINE);
        pairField.setMinLines(2);
        pairField.setGravity(Gravity.TOP | Gravity.START);
        card.addView(pairField, lp(0, 6));

        card.addView(Ui.txt(this, "Имя устройства", 11.5f, Ui.MUTED, false), lp(0, 12));
        nameField = Ui.edit(this, "Например, Телефон сына", "");
        card.addView(nameField, lp(0, 6));

        LinearLayout.LayoutParams blp = lp(0, 14);
        card.addView(Ui.primary(this, "Сохранить привязку", new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                savePairing();
            }
        }), blp);

        card.addView(Ui.ghost(this, "Проверить связь", new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                SyncService.start(MainActivity.this);
                Ui.toast(MainActivity.this, "Синхронизация запущена");
            }
        }), lp(0, 8));

        card.addView(Ui.txt(this, "Код создаётся в консоли родителя: "
                        + "ребёнок → «Привязать». Работает в домашней сети и через туннель.",
                11.5f, Ui.MUTED, false), lp(0, 10));
    }

    @Override
    protected void onActivityResult(int req, int res, Intent data) {
        super.onActivityResult(req, res, data);
        if (req != 71) return;
        if (res == RESULT_OK && data != null) {
            String code = data.getStringExtra(ScanActivity.EXTRA_PAIRING);
            if (code != null && !code.trim().isEmpty()) {
                pairField.setText(code.trim());
                Ui.toast(this, "Код считан — проверьте и нажмите «Сохранить привязку»");
                scrollToPairing();
            }
        } else if (res == RESULT_CANCELED) {
            Ui.toast(this, "QR не считан — введите код вручную");
        }
    }

    private void scrollToPairing() {
        if (pairCard == null) return;
        scroll.post(new Runnable() {
            @Override
            public void run() {
                scroll.smoothScrollTo(0, pairCard.getTop());
            }
        });
    }

    private void savePairing() {
        String raw = pairField.getText().toString().trim();
        String[] parts = raw.split(":", 5);
        if (parts.length != 5 || !parts[0].equalsIgnoreCase("hg1")) {
            Ui.toast(this, "Формат: hg1:IP[+IP_ТУННЕЛЯ]:PORT:ID:КОД");
            return;
        }
        String host = parts[1];
        int port;
        try {
            port = Integer.parseInt(parts[2]);
        } catch (Exception e) {
            Ui.toast(this, "Порт не число");
            return;
        }
        String deviceId = parts[3];
        String code = parts[4];
        if (Protocol.normalizeCode(code).length() < 8) {
            Ui.toast(this, "Код слишком короткий");
            return;
        }
        final List<String> urls = new ArrayList<>();
        for (String hst : host.split("\\+")) {
            String t = hst.trim();
            if (t.isEmpty()) continue;
            if (!privateHost(t)) {
                Ui.toast(this, "Только адрес домашней сети: 192.168.x, 10.x, 172.16–31.x");
                return;
            }
            urls.add("http://" + t + ":" + port);
        }
        if (urls.isEmpty()) {
            Ui.toast(this, "Адрес не задан");
            return;
        }
        final String fid = deviceId;
        final String fcode = Protocol.normalizeCode(code);
        StringBuilder where = new StringBuilder();
        for (String u : urls) where.append("\n• ").append(u.replace("http://", ""));
        new android.app.AlertDialog.Builder(this)
                .setTitle("Привязать к этой консоли?")
                .setMessage("Адрес:" + where + "\nID: " + fid
                        + "\n\nСверьте адрес с консолью родителя: телефон будет выполнять"
                        + " только её команды. Чужой «код привязки» может забрать контроль.")
                .setNegativeButton("Отмена", null)
                .setPositiveButton("Привязать", new android.content.DialogInterface.OnClickListener() {
                    @Override
                    public void onClick(android.content.DialogInterface d, int w) {
                        commitPairing(urls, fid, fcode);
                    }
                })
                .show();
    }

    /** Accepts IPv4 literals inside RFC1918 / loopback / link-local only. */
    private boolean privateHost(String h) {
        try {
            String[] p = h.split("\\.");
            if (p.length != 4) return false;
            int a = Integer.parseInt(p[0]);
            int b = Integer.parseInt(p[1]);
            int c = Integer.parseInt(p[2]);
            int d = Integer.parseInt(p[3]);
            if (a < 0 || a > 255 || b < 0 || b > 255 || c < 0 || c > 255 || d < 0 || d > 255) {
                return false;
            }
            if (a == 10 || a == 127) return true;
            if (a == 172 && b >= 16 && b <= 31) return true;
            if (a == 192 && b == 168) return true;
            return a == 169 && b == 254;
        } catch (Exception e) {
            return false;
        }
    }

    private void commitPairing(List<String> urls, String deviceId, String code) {
        try {
            Store.setSecret(this, code);
            Store.setServers(this, urls);
            Store.put(this, "device_id", deviceId);
            String name = nameField.getText().toString().trim();
            if (!name.isEmpty()) Store.put(this, "device_name", name);
            Store.putInt(this, "policy_v", -1);
            Ui.toast(this, "Привязка сохранена");
            SyncService.start(this);
            render();
        } catch (Exception e) {
            Ui.toast(this, "Не удалось сохранить: " + e.getMessage());
        }
    }

    // ------------------------------------------------------------- actions

    private void askAdmin() {
        try {
            Intent i = new Intent(DevicePolicyManager.ACTION_ADD_DEVICE_ADMIN);
            i.putExtra(DevicePolicyManager.EXTRA_DEVICE_ADMIN, Admin.cn(this));
            i.putExtra(DevicePolicyManager.EXTRA_ADD_EXPLANATION,
                    "Нужно для управления этим телефоном из консоли родителя.");
            startActivity(i);
        } catch (Exception e) {
            Ui.toast(this, "Настройки → Безопасность → Администраторы устройства");
        }
    }

    private void askNotifications() {
        if (Admin.isOwner(this)) {
            Admin.grantPermission(this, Manifest.permission.POST_NOTIFICATIONS);
            Ui.toast(this, "Разрешение выдано владельцем устройства");
            render();
            return;
        }
        requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, 10);
    }

    private void askLocation() {
        if (Admin.isOwner(this)) {
            Admin.grantPermission(this, Manifest.permission.ACCESS_FINE_LOCATION);
            Admin.grantPermission(this, Manifest.permission.ACCESS_BACKGROUND_LOCATION);
            Ui.toast(this, "Разрешение выдано владельцем устройства");
            render();
            return;
        }
        List<String> need = new ArrayList<>();
        for (String p : new String[]{Manifest.permission.ACCESS_FINE_LOCATION,
                Manifest.permission.ACCESS_COARSE_LOCATION}) {
            if (checkSelfPermission(p) != PackageManager.PERMISSION_GRANTED) need.add(p);
        }
        if (!need.isEmpty()) requestPermissions(need.toArray(new String[0]), 11);
    }

    private void askBattery() {
        try {
            Intent i = new Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS);
            i.setData(Uri.parse("package:" + getPackageName()));
            startActivity(i);
        } catch (Exception e) {
            Ui.openSettings(this, Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS, null);
        }
    }

    @Override
    public void onRequestPermissionsResult(int code, String[] perms, int[] res) {
        super.onRequestPermissionsResult(code, perms, res);
        render();
    }

    // --------------------------------------------------------------- checks

    private boolean granted(String perm) {
        try {
            return checkSelfPermission(perm) == PackageManager.PERMISSION_GRANTED;
        } catch (Exception e) {
            return false;
        }
    }

    private boolean usageAccess() {
        try {
            AppOpsManager ops = (AppOpsManager) getSystemService(APP_OPS_SERVICE);
            if (ops == null) return false;
            int mode = ops.unsafeCheckOpNoThrow(AppOpsManager.OPSTR_GET_USAGE_STATS,
                    Process.myUid(), getPackageName());
            return mode == AppOpsManager.MODE_ALLOWED;
        } catch (Exception e) {
            return false;
        }
    }

    private boolean a11yOn() {
        try {
            String cur = Settings.Secure.getString(getContentResolver(),
                    Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES);
            return cur != null && cur.contains(getPackageName()) && cur.contains("AccessService");
        } catch (Exception e) {
            return false;
        }
    }

    private boolean batteryFree() {
        try {
            PowerManager pm = (PowerManager) getSystemService(POWER_SERVICE);
            return pm != null && pm.isIgnoringBatteryOptimizations(getPackageName());
        } catch (Exception e) {
            return false;
        }
    }

    private boolean adbOn() {
        try {
            return Settings.Global.getInt(getContentResolver(), Settings.Global.ADB_ENABLED, 0) == 1;
        } catch (Exception e) {
            return false;
        }
    }

    // ---------------------------------------------------------------- misc

    private String ago(long ts) {
        if (ts <= 0) return "—";
        long diff = System.currentTimeMillis() - ts;
        if (diff < 60_000L) return "только что";
        if (diff < 3_600_000L) return (diff / 60_000L) + " мин назад";
        if (diff < 86_400_000L) return (diff / 3_600_000L) + " ч назад";
        return new java.text.SimpleDateFormat("dd.MM HH:mm", java.util.Locale.US)
                .format(new java.util.Date(ts));
    }

    private View footer() {
        LinearLayout c = Ui.col(this);
        c.setGravity(Gravity.CENTER);
        TextView v = Ui.txt(this, "HomeGuard Агент " + version(), 11.5f, Ui.MUTED, false);
        v.setGravity(Gravity.CENTER);
        c.addView(v);
        TextView n = Ui.txt(this, "Данные не покидают вашу сеть", 11.5f, Ui.MUTED, false);
        n.setGravity(Gravity.CENTER);
        c.addView(n, lp(0, 3));
        return c;
    }

    private String version() {
        try {
            return getPackageManager().getPackageInfo(getPackageName(), 0).versionName;
        } catch (Exception e) {
            return "";
        }
    }

    private LinearLayout.LayoutParams lp(int horizontal, int top) {
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        p.topMargin = Ui.dp(this, top);
        if (horizontal > 0) {
            p.leftMargin = Ui.dp(this, horizontal);
            p.rightMargin = Ui.dp(this, horizontal);
        }
        return p;
    }
}
