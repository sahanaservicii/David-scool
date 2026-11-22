package ru.homeguard.console;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.DialogInterface;
import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.View;
import android.view.ViewGroup;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import org.json.JSONObject;

/** One child: live state, quick actions, policy entry points. */
public class DeviceActivity extends Activity {

    private final Handler h = new Handler(Looper.getMainLooper());
    private String id;
    private Db db;
    private LinearLayout hero;
    private LinearLayout screenCard;
    private LinearLayout details;

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
        id = getIntent().getStringExtra("device");
        db = Db.get(this);
        Db.Device d = db.device(id);
        if (d == null) {
            finish();
            return;
        }

        ScrollView sc = Ui.scroll(this);
        LinearLayout body = Ui.body(sc);

        hero = Ui.col(this);
        body.addView(hero);
        screenCard = Ui.col(this);
        body.addView(screenCard, top(12));

        body.addView(Ui.sectionTitle(this, "Быстрые действия"));
        body.addView(Ui.tiles(this,
                Ui.actionTile(this, R.drawable.ic_lock, "Блокировать", Ui.ORANGE,
                        new View.OnClickListener() {
                            @Override
                            public void onClick(View v) {
                                cmd("lock", null);
                            }
                        }),
                Ui.actionTile(this, R.drawable.ic_check, "Разблокировать", Ui.GREEN,
                        new View.OnClickListener() {
                            @Override
                            public void onClick(View v) {
                                cmd("unlock", null);
                            }
                        }),
                Ui.actionTile(this, R.drawable.ic_pin, "Где он", Ui.BLUE,
                        new View.OnClickListener() {
                            @Override
                            public void onClick(View v) {
                                cmd("locate", null);
                            }
                        }),
                Ui.actionTile(this, R.drawable.ic_link, "Код", Ui.VIOLET,
                        new View.OnClickListener() {
                            @Override
                            public void onClick(View v) {
                                showPairing();
                            }
                        })));

        body.addView(Ui.sectionTitle(this, "Управление"));
        LinearLayout manage = Ui.card(this);
        manage.addView(Ui.rowItem(this, R.drawable.ic_shield, "Правила и расписание",
                "Что разрешено и когда", Ui.BLUE, new View.OnClickListener() {
                    @Override
                    public void onClick(View v) {
                        open(PolicyActivity.class);
                    }
                }));
        manage.addView(Ui.divider(this));
        manage.addView(Ui.rowItem(this, R.drawable.ic_chart, "Отчёты и события",
                "Экранное время и приложения", Ui.VIOLET, new View.OnClickListener() {
                    @Override
                    public void onClick(View v) {
                        open(ReportsActivity.class);
                    }
                }));
        manage.addView(Ui.divider(this));
        manage.addView(Ui.rowItem(this, R.drawable.ic_link, "Код привязки",
                "Ввести заново на телефоне", Ui.MUTED, new View.OnClickListener() {
                    @Override
                    public void onClick(View v) {
                        showPairing();
                    }
                }));
        body.addView(manage, top(8));

        details = Ui.col(this);
        body.addView(details, top(12));

        body.addView(Ui.sectionTitle(this, "Опасные действия"));
        LinearLayout danger = Ui.card(this);
        danger.addView(Ui.txt(this, "Изменения на телефоне ребёнка", 14, Ui.INK, true));
        TextView note = Ui.txt(this, "Каждое действие требует подтверждения.", 12, Ui.MUTED, false);
        note.setPadding(0, Ui.dp(this, 4), 0, Ui.dp(this, 8));
        danger.addView(note);
        danger.addView(Ui.soft(this, "Перезагрузить телефон", Ui.ORANGE,
                new View.OnClickListener() {
                    @Override
                    public void onClick(View v) {
                        confirm("Перезагрузить телефон ребёнка?", "reboot", null);
                    }
                }), top(6));
        danger.addView(Ui.danger(this, "Стереть все данные", new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                confirm("Стереть все данные телефона ребёнка? Это необратимо.",
                        "wipe", new JSONObject());
            }
        }), top(8));
        danger.addView(Ui.danger(this, "Удалить из консоли", new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                removeDevice();
            }
        }), top(8));
        body.addView(danger, top(8));

        setContentView(Ui.page(this,
                Ui.headerBack(this, d.name, "управление устройством"), sc, -1));
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
        Db.Device d = db.device(id);
        if (d == null) {
            finish();
            return;
        }
        JSONObject st = d.state();

        hero.removeAllViews();
        hero.addView(heroCard(d, st), top(8));

        screenCard.removeAllViews();
        screenCard.addView(screenCard(d, st));

        details.removeAllViews();
        details.addView(detailsCard(d, st));
    }

    private View heroCard(Db.Device d, JSONObject st) {
        LinearLayout card = Ui.card(this);
        LinearLayout r = Ui.row(this);
        r.addView(Ui.avatar(this, d.name, 54));

        LinearLayout col = Ui.col(this);
        col.setPadding(Ui.dp(this, 14), 0, 0, 0);
        col.addView(Ui.txt(this, d.name, 18, Ui.INK, true));
        col.addView(Ui.txt(this, st.optString("model", "—"), 12.5f, Ui.MUTED, false));
        r.addView(col, new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f));

        boolean online = d.online();
        r.addView(Ui.pill(this, online ? "на связи" : "офлайн",
                online ? 0xFF15803D : 0xFF6B7280,
                online ? 0x1A22C55E : 0x14000000));
        card.addView(r);

        LinearLayout chips = Ui.row(this);
        chips.setPadding(0, Ui.dp(this, 14), 0, 0);
        boolean isDo = st.optBoolean("do", false);
        chips.addView(Ui.pill(this, isDo ? "Device Owner" : "не Device Owner",
                isDo ? 0xFF15803D : 0xFFB91C1C, isDo ? 0x1A22C55E : 0x1AEF4444));
        int battery = st.optInt("battery", -1);
        if (battery >= 0) {
            int tint = battery < 15 ? Ui.RED : battery < 35 ? Ui.ORANGE : Ui.GREEN;
            View b = Ui.pill(this, battery + "%" + (st.optBoolean("charging", false) ? " ⚡" : ""),
                    tint, Ui.alpha(tint, 0x1A));
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
            lp.leftMargin = Ui.dp(this, 8);
            chips.addView(b, lp);
        }
        card.addView(chips);
        return card;
    }

    private View screenCard(Db.Device d, JSONObject st) {
        LinearLayout card = Ui.card(this);
        long today = st.optInt("today_min", 0);
        int limit = d.policy.optInt("daily_limit_min", 0);
        long base = limit > 0 ? limit : 240;
        float pct = Math.max(0f, Math.min(1f, today / (float) base));

        LinearLayout r = Ui.row(this);

        FrameLayout ringBox = new FrameLayout(this);
        Ui.Ring ring = new Ui.Ring(this);
        ring.set(pct, pct > 0.9f ? Ui.RED : pct > 0.7f ? Ui.ORANGE : Ui.BLUE,
                String.valueOf(today), "мин");
        ringBox.addView(ring, new FrameLayout.LayoutParams(Ui.dp(this, 104), Ui.dp(this, 104)));
        LinearLayout.LayoutParams rlp = new LinearLayout.LayoutParams(
                Ui.dp(this, 104), Ui.dp(this, 104));
        rlp.rightMargin = Ui.dp(this, 16);
        r.addView(ringBox, rlp);

        LinearLayout col = Ui.col(this);
        col.addView(Ui.txt(this, "Экран сегодня", 13, Ui.MUTED, false));
        col.addView(Ui.txt(this, Ui.minutes(today), 20, Ui.INK, true));
        col.addView(Ui.txt(this, limit > 0 ? "лимит " + Ui.minutes(limit) : "лимит не задан",
                12, Ui.INK2, false));

        boolean locked = st.optBoolean("locked", false);
        TextView state = Ui.txt(this, locked
                ? "заблокирован · " + st.optString("lock_reason", "да")
                : "экран свободен", 12, locked ? Ui.ORANGE : Ui.GREEN, false);
        state.setPadding(0, Ui.dp(this, 6), 0, 0);
        col.addView(state);
        r.addView(col, new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        card.addView(r);

        return card;
    }

    private View detailsCard(Db.Device d, JSONObject st) {
        LinearLayout card = Ui.card(this);
        card.addView(infoRow("Android", st.optString("android", "—")
                + " · SDK " + st.optInt("sdk", 0)));
        card.addView(infoRow("Правила", "v" + d.policyV + " · на телефоне v"
                + st.optInt("policy_v", -1)));
        card.addView(infoRow("Экран", st.optBoolean("screen", false)
                ? "включён" : "выключен"));
        card.addView(infoRow("В фоне", st.optString("fg", "—")));
        card.addView(infoRow("Последняя связь", d.online() ? "сейчас" : Util.ago(d.lastSeen)));
        JSONObject loc = st.optJSONObject("loc");
        if (loc != null && loc.has("lat")) {
            card.addView(infoRow("Геопозиция", String.format(java.util.Locale.US,
                    "%.5f, %.5f", loc.optDouble("lat"), loc.optDouble("lon"))));
        }
        return card;
    }

    private View infoRow(String label, String value) {
        LinearLayout r = Ui.row(this);
        r.setPadding(0, Ui.dp(this, 9), 0, Ui.dp(this, 9));
        r.addView(Ui.txt(this, label, 13, Ui.MUTED, false),
                new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        TextView v = Ui.txt(this, value, 13, Ui.INK, false);
        v.setGravity(android.view.Gravity.END);
        r.addView(v);
        return r;
    }

    private void open(Class<?> cls) {
        Intent i = new Intent(this, cls);
        i.putExtra("device", id);
        startActivity(i);
    }

    private void cmd(String type, JSONObject args) {
        Db.Device d = db.device(id);
        if (d == null) {
            finish();
            return;
        }
        if (!d.online()) {
            Ui.toast(this, "Телефон офлайн — команда уйдёт при подключении");
        }
        db.queueCommand(id, type, args);
        Ui.toast(this, "Команда в очереди");
        render();
    }

    private void confirm(String text, final String type, final JSONObject baseArgs) {
        new AlertDialog.Builder(this)
                .setMessage(text)
                .setPositiveButton("Да", new DialogInterface.OnClickListener() {
                    @Override
                    public void onClick(DialogInterface dialog, int which) {
                        try {
                            JSONObject a = baseArgs == null ? new JSONObject() : baseArgs;
                            if ("wipe".equals(type)) a.put("confirm", "WIPE");
                            cmd(type, a);
                        } catch (Exception ignored) {}
                    }
                })
                .setNegativeButton("Отмена", null)
                .show();
    }

    private void removeDevice() {
        new AlertDialog.Builder(this)
                .setMessage("Удалить устройство и историю? Агент перестанет подключаться.")
                .setPositiveButton("Удалить", new DialogInterface.OnClickListener() {
                    @Override
                    public void onClick(DialogInterface d, int w) {
                        db.removeDevice(id);
                        finish();
                    }
                })
                .setNegativeButton("Отмена", null)
                .show();
    }

    /** Pairing string can be re-entered on the agent to change endpoints (LAN/WG). */
    private void showPairing() {
        final Db.Device d = db.device(id);
        if (d == null || d.secret == null) {
            Ui.toast(this, "Секрет недоступен — создайте устройство заново");
            return;
        }
        StringBuilder pretty = new StringBuilder();
        String s = d.secret;
        for (int i = 0; i < s.length(); i++) {
            if (i > 0 && i % 4 == 0) pretty.append('-');
            pretty.append(s.charAt(i));
        }
        String lan = Util.localIp();
        final String plain = Protocol.pairing(lan, ControlServer.PORT, d.id, pretty.toString());
        String withWg = "hg1:" + lan + "+<WG-IP>:" + ControlServer.PORT + ":" + d.id + ":" + pretty;
        new AlertDialog.Builder(this)
                .setTitle("Код привязки")
                .setMessage(plain + "\n\nДома работает по LAN. Чтобы добавить туннель, "
                        + "введите в агенте строку с двумя адресами через «+»:\n\n" + withWg)
                .setPositiveButton("Копировать", new DialogInterface.OnClickListener() {
                    @Override
                    public void onClick(DialogInterface dlg, int w) {
                        Ui.copy(DeviceActivity.this, plain);
                        Ui.toast(DeviceActivity.this, "Скопировано");
                    }
                })
                .setNegativeButton("Закрыть", null)
                .show();
    }
}
