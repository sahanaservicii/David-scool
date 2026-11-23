package ru.homeguard.console;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ContentValues;
import android.content.DialogInterface;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.os.Environment;
import android.os.Handler;
import android.os.Looper;
import android.provider.MediaStore;
import android.view.View;
import android.view.ViewGroup;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import java.io.InputStream;
import java.io.OutputStream;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

/** Tab 4: server address, children list, about. */
public class SettingsActivity extends Activity {

    private final Handler h = new Handler(Looper.getMainLooper());
    private LinearLayout server;
    private LinearLayout kids;
    private LinearLayout data;
    private static final int REQ_RESTORE = 41;

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
        ScrollView sc = Ui.scroll(this);
        LinearLayout body = Ui.body(sc);

        server = Ui.col(this);
        body.addView(server);

        body.addView(Ui.sectionTitle(this, "Дети"));
        kids = Ui.col(this);
        body.addView(kids);

        body.addView(Ui.sectionTitle(this, "Данные"));
        data = Ui.col(this);
        body.addView(data);

        body.addView(Ui.sectionTitle(this, "О приложении"));
        body.addView(aboutCard());

        setContentView(Ui.page(this,
                Ui.header(this, "КОНСОЛЬ", "Настройки", "Сервер, дети и данные"),
                sc, Ui.TAB_SETTINGS));
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
        server.removeAllViews();
        server.addView(serverCard(), top(8));

        kids.removeAllViews();
        LinearLayout list = Ui.card(this);
        boolean first = true;
        for (final Db.Device d : Db.get(this).devices()) {
            if (!first) list.addView(Ui.divider(this));
            first = false;
            list.addView(Ui.rowItem(this, R.drawable.ic_users, d.name,
                    d.online() ? "на связи" : "офлайн · " + Util.ago(d.lastSeen),
                    Ui.tintFor(d.name), new View.OnClickListener() {
                        @Override
                        public void onClick(View v) {
                            Intent i = new Intent(SettingsActivity.this, DeviceActivity.class);
                            i.putExtra("device", d.id);
                            startActivity(i);
                        }
                    }));
        }
        if (!first) list.addView(Ui.divider(this));
        list.addView(Ui.rowItem(this, R.drawable.ic_plus, "Добавить ребёнка",
                "Код привязки для нового телефона", Ui.BLUE, new View.OnClickListener() {
                    @Override
                    public void onClick(View v) {
                        startActivity(new Intent(SettingsActivity.this, PairingActivity.class));
                    }
                }));
        kids.addView(list, top(8));

        data.removeAllViews();
        data.addView(dataCard(), top(8));
    }

    private LinearLayout.LayoutParams top(int dp) {
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        lp.topMargin = Ui.dp(this, dp);
        return lp;
    }

    private View serverCard() {
        LinearLayout card = Ui.card(this);

        LinearLayout head = Ui.row(this);
        head.addView(Ui.txt(this, "Сервер", 16, Ui.INK, true),
                new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        boolean alive = ConsoleService.alive;
        head.addView(Ui.pill(this, alive ? "работает" : "остановлен",
                alive ? 0xFF15803D : 0xFFB91C1C,
                alive ? 0x1A22C55E : 0x1AEF4444));
        card.addView(head);

        String ip = Util.localIp();
        card.addView(infoRow("Адрес", "http://" + ip + ":" + ControlServer.PORT));
        StringBuilder all = new StringBuilder();
        for (String s : Util.localIps()) {
            if (all.length() > 0) all.append(", ");
            all.append(s);
        }
        card.addView(infoRow("Все адреса", all.length() == 0 ? "нет" : all.toString()));
        card.addView(infoRow("Сеть", Util.wifiName(this)));

        // Local HA webhook (optional). Empty = disabled; no token in the app.
        final android.widget.EditText hook = Ui.edit(this,
                "http://192.168.1.156:8123/api/webhook/homeguard_sos_bridge",
                HaBridge.url(this));
        hook.setSingleLine(true);
        card.addView(hook);
        LinearLayout haRow = Ui.row(this);
        haRow.setPadding(0, Ui.dp(this, 10), 0, 0);
        haRow.addView(Ui.txt(this, "Мост в Home Assistant", 13, Ui.MUTED, false),
                new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        android.widget.Button haSave = Ui.ghost(this, "Сохранить", new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                HaBridge.setUrl(SettingsActivity.this, hook.getText().toString());
                Ui.toast(SettingsActivity.this,
                        HaBridge.enabled(SettingsActivity.this)
                                ? "Мост включён" : "Мост выключен");
            }
        });
        haRow.addView(haSave);
        card.addView(haRow);

        LinearLayout actions = Ui.row(this);
        actions.setPadding(0, Ui.dp(this, 12), 0, 0);
        android.widget.Button ping = Ui.ghost(this, "Проверить", new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                ping();
            }
        });
        android.widget.Button copy = Ui.ghost(this, "Скопировать адрес",
                new View.OnClickListener() {
                    @Override
                    public void onClick(View v) {
                        Ui.copy(SettingsActivity.this,
                                "http://" + Util.localIp() + ":" + ControlServer.PORT);
                        Ui.toast(SettingsActivity.this, "Адрес скопирован");
                    }
                });
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        actions.addView(ping, lp);
        LinearLayout.LayoutParams lp2 = new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        lp2.leftMargin = Ui.dp(this, 10);
        actions.addView(copy, lp2);
        card.addView(actions);
        return card;
    }

    private View infoRow(String label, String value) {
        LinearLayout r = Ui.row(this);
        r.setPadding(0, Ui.dp(this, 11), 0, Ui.dp(this, 11));
        r.addView(Ui.txt(this, label, 13, Ui.MUTED, false),
                new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        android.widget.TextView v = Ui.txt(this, value, 13, Ui.INK, false);
        v.setGravity(android.view.Gravity.END);
        r.addView(v);
        return r;
    }

    private View aboutCard() {
        LinearLayout card = Ui.card(this);
        String version = "1.2.0";
        try {
            version = getPackageManager().getPackageInfo(getPackageName(), 0).versionName;
        } catch (Exception ignored) {}
        card.addView(infoRow("Версия", version));
        card.addView(infoRow("Порт", String.valueOf(ControlServer.PORT)));
        card.addView(infoRow("Хранение", "только этот телефон"));
        card.addView(infoRow("История", "события 120 дней"));
        card.addView(infoRow("Транспорт", "LAN + WireGuard"));
        android.widget.TextView note = Ui.txt(this,
                "Консоль не использует интернет: данные идут напрямую между вашим "
                        + "телефоном и телефоном ребёнка в вашей сети или туннеле.",
                12, Ui.MUTED, false);
        note.setPadding(0, Ui.dp(this, 10), 0, 0);
        card.addView(note);
        return card;
    }

    private void ping() {
        new Thread(new Runnable() {
            @Override
            public void run() {
                String result;
                java.net.HttpURLConnection c = null;
                try {
                    c = (java.net.HttpURLConnection) new java.net.URL(
                            "http://127.0.0.1:" + ControlServer.PORT
                                    + Protocol.PATH_PING).openConnection();
                    c.setConnectTimeout(3000);
                    c.setReadTimeout(3000);
                    result = c.getResponseCode() == 200
                            ? "Сервер отвечает: OK" : "Ответ " + c.getResponseCode();
                } catch (Exception e) {
                    result = "Сервер не отвечает: " + e.getClass().getSimpleName();
                } finally {
                    if (c != null) c.disconnect();
                }
                final String r = result;
                runOnUiThread(new Runnable() {
                    @Override
                    public void run() {
                        Ui.toast(SettingsActivity.this, r);
                    }
                });
            }
        }).start();
    }

    // ---------------- data: backup, restore, crash log ----------------

    private View dataCard() {
        LinearLayout card = Ui.card(this);
        card.addView(Ui.rowItem(this, R.drawable.ic_shield, "Резервная копия",
                "дети, правила и история в зашифрованном файле", Ui.BLUE,
                new View.OnClickListener() {
                    @Override
                    public void onClick(View v) {
                        backupDialog();
                    }
                }));
        card.addView(Ui.divider(this));
        card.addView(Ui.rowItem(this, R.drawable.ic_link, "Восстановить из копии",
                "файл .hgbak и пароль", Ui.VIOLET, new View.OnClickListener() {
                    @Override
                    public void onClick(View v) {
                        pickBackup();
                    }
                }));
        card.addView(Ui.divider(this));
        card.addView(Ui.rowItem(this, R.drawable.ic_warning, "Лог сбоев",
                CrashLog.summary(this), Ui.MUTED, new View.OnClickListener() {
                    @Override
                    public void onClick(View v) {
                        crashDialog();
                    }
                }));
        card.addView(Ui.divider(this));
        card.addView(Ui.rowItem(this, R.drawable.ic_trash, "Очистить историю",
                "события и статистика, дети останутся", Ui.RED,
                new View.OnClickListener() {
                    @Override
                    public void onClick(View v) {
                        clearHistory();
                    }
                }));
        return card;
    }

    private void backupDialog() {
        final EditText pass = Ui.edit(this, "пароль, минимум 6 символов", "");
        pass.setInputType(android.text.InputType.TYPE_CLASS_TEXT
                | android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD);
        new AlertDialog.Builder(this)
                .setTitle("Резервная копия")
                .setMessage("Файл шифруется паролем и сохраняется в «Загрузки/HomeGuard». "
                        + "Пароль нигде не хранится: без него копию не открыть.")
                .setView(pass)
                .setPositiveButton("Создать", new DialogInterface.OnClickListener() {
                    @Override
                    public void onClick(DialogInterface d, int w) {
                        runBackup(pass.getText().toString());
                    }
                })
                .setNegativeButton("Отмена", null)
                .show();
    }

    private void runBackup(final String pass) {
        new Thread(new Runnable() {
            @Override
            public void run() {
                String result;
                try {
                    String blob = Backup.create(Db.get(SettingsActivity.this), pass);
                    String name = "homeguard-"
                            + new SimpleDateFormat("yyyyMMdd-HHmm", Locale.US)
                            .format(new Date()) + ".hgbak";
                    saveToDownloads(name, blob);
                    result = "Сохранено: Загрузки/HomeGuard/" + name;
                } catch (Exception e) {
                    result = "Не получилось: " + e.getMessage();
                }
                final String r = result;
                runOnUiThread(new Runnable() {
                    @Override
                    public void run() {
                        render();
                        Ui.toast(SettingsActivity.this, r);
                    }
                });
            }
        }, "hg-backup").start();
    }

    private void saveToDownloads(String name, String text) throws Exception {
        ContentValues v = new ContentValues();
        v.put(MediaStore.Downloads.DISPLAY_NAME, name);
        v.put(MediaStore.Downloads.MIME_TYPE, "application/octet-stream");
        v.put(MediaStore.Downloads.RELATIVE_PATH,
                Environment.DIRECTORY_DOWNLOADS + "/HomeGuard");
        Uri uri = getContentResolver().insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, v);
        if (uri == null) throw new IllegalStateException("нет доступа к Загрузкам");
        try (OutputStream out = getContentResolver().openOutputStream(uri)) {
            if (out == null) throw new IllegalStateException("не удалось записать файл");
            out.write(Protocol.utf8(text));
        }
    }

    private void pickBackup() {
        Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        i.addCategory(Intent.CATEGORY_OPENABLE);
        i.setType("*/*");
        startActivityForResult(i, REQ_RESTORE);
    }

    @Override
    protected void onActivityResult(int req, int res, Intent data) {
        super.onActivityResult(req, res, data);
        if (req != REQ_RESTORE || res != RESULT_OK || data == null || data.getData() == null) {
            return;
        }
        final Uri uri = data.getData();
        final EditText pass = Ui.edit(this, "пароль от копии", "");
        pass.setInputType(android.text.InputType.TYPE_CLASS_TEXT
                | android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD);
        new AlertDialog.Builder(this)
                .setTitle("Восстановить данные")
                .setMessage("Записи с теми же id заменятся. Остальные дети не тронуты. "
                        + "Старые события не удаляются.")
                .setView(pass)
                .setPositiveButton("Восстановить", new DialogInterface.OnClickListener() {
                    @Override
                    public void onClick(DialogInterface d, int w) {
                        runRestore(uri, pass.getText().toString());
                    }
                })
                .setNegativeButton("Отмена", null)
                .show();
    }

    private void runRestore(final Uri uri, final String pass) {
        new Thread(new Runnable() {
            @Override
            public void run() {
                String result;
                try (InputStream in = getContentResolver().openInputStream(uri)) {
                    if (in == null) throw new IllegalStateException("файл недоступен");
                    java.io.ByteArrayOutputStream buf = new java.io.ByteArrayOutputStream();
                    byte[] chunk = new byte[8192];
                    int n;
                    while ((n = in.read(chunk)) > 0) buf.write(chunk, 0, n);
                    String summary = Backup.restore(Db.get(SettingsActivity.this),
                            new String(buf.toByteArray(), "UTF-8"), pass);
                    result = "Восстановлено: " + summary;
                } catch (Exception e) {
                    result = "Не получилось: " + e.getMessage();
                }
                final String r = result;
                runOnUiThread(new Runnable() {
                    @Override
                    public void run() {
                        render();
                        Ui.toast(SettingsActivity.this, r);
                    }
                });
            }
        }, "hg-restore").start();
    }

    private void crashDialog() {
        final String log = CrashLog.read(this);
        if (log == null) {
            Ui.toast(this, "Сбоев не было");
            return;
        }
        final String shown = log.length() > 6000 ? log.substring(log.length() - 6000) : log;
        new AlertDialog.Builder(this)
                .setTitle("Лог сбоев")
                .setMessage(shown)
                .setPositiveButton("Копировать", new DialogInterface.OnClickListener() {
                    @Override
                    public void onClick(DialogInterface d, int w) {
                        Ui.copy(SettingsActivity.this, shown);
                        Ui.toast(SettingsActivity.this, "Скопировано");
                    }
                })
                .setNeutralButton("Очистить", new DialogInterface.OnClickListener() {
                    @Override
                    public void onClick(DialogInterface d, int w) {
                        CrashLog.clear(SettingsActivity.this);
                        render();
                    }
                })
                .setNegativeButton("Закрыть", null)
                .show();
    }

    private void clearHistory() {
        new AlertDialog.Builder(this)
                .setMessage("Удалить события и статистику? Дети и правила останутся.")
                .setPositiveButton("Удалить", new DialogInterface.OnClickListener() {
                    @Override
                    public void onClick(DialogInterface d, int w) {
                        Db db = Db.get(SettingsActivity.this);
                        db.getWritableDatabase().delete("events", null, null);
                        db.getWritableDatabase().delete("usage", null, null);
                        render();
                        Ui.toast(SettingsActivity.this, "История очищена");
                    }
                })
                .setNegativeButton("Отмена", null)
                .show();
    }
}
