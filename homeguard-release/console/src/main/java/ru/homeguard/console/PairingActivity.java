package ru.homeguard.console;

import android.app.Activity;
import android.os.Bundle;
import android.view.View;
import android.view.ViewGroup;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import java.security.SecureRandom;

/** Creates a child and shows the pairing code for the agent. */
public class PairingActivity extends Activity {

    private EditText name;
    private EditText wgHost;
    private LinearLayout result;

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        // Pairing code is the device secret: keep it out of screenshots and recents.
        getWindow().setFlags(android.view.WindowManager.LayoutParams.FLAG_SECURE,
                android.view.WindowManager.LayoutParams.FLAG_SECURE);
        ScrollView sc = Ui.scroll(this);
        LinearLayout body = Ui.body(sc);

        LinearLayout who = Ui.card(this);
        who.addView(Ui.txt(this, "Имя ребёнка", 14, Ui.INK, true));
        who.addView(Ui.txt(this, "Так карточка будет называться в консоли",
                12, Ui.MUTED, false));
        name = Ui.edit(this, "Миша", "");
        who.addView(name, top(8));
        body.addView(who, top(8));

        LinearLayout net = Ui.card(this);
        net.addView(Ui.txt(this, "Адрес в WireGuard", 14, Ui.INK, true));
        net.addView(Ui.txt(this, "Необязательно. Если укажете адрес этого телефона "
                + "в туннеле, агент будет работать и дома (LAN), и вне дома.",
                12, Ui.MUTED, false));
        wgHost = Ui.edit(this, "192.168.9.2", "");
        net.addView(wgHost, top(8));
        body.addView(net, top(10));

        body.addView(Ui.primary(this, "Создать код привязки", new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                create();
            }
        }), top(16));

        result = Ui.col(this);
        body.addView(result);

        LinearLayout how = Ui.card(this);
        how.addView(Ui.txt(this, "Как подключить", 14, Ui.INK, true));
        how.addView(Ui.txt(this,
                "1. Установите агент на телефон ребёнка.\n"
                        + "2. Нажмите «Сканировать QR» в агенте и наведите камеру "
                        + "на код ниже — привязка выполнится сама.\n"
                        + "3. Если камера не сработает — введите ту же строку вручную.\n"
                        + "4. Выдайте Device Owner (сброс телефона) — тогда доступны "
                        + "блокировки, камера и запрет установок.",
                13, Ui.INK2, false), top(8));
        how.addView(Ui.txt(this,
                "Телефон ребёнка и эта консоль должны быть в одной сети "
                        + "или в вашем WireGuard-туннеле.",
                12, Ui.MUTED, false), top(10));
        body.addView(how, top(18));

        setContentView(Ui.page(this,
                Ui.headerBack(this, "Новый ребёнок", "код привязки для его телефона"),
                sc, -1));
    }

    private LinearLayout.LayoutParams top(int dp) {
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        lp.topMargin = Ui.dp(this, dp);
        return lp;
    }

    private void create() {
        String n = name.getText().toString().trim();
        if (n.isEmpty()) n = "Ребёнок";

        byte[] raw = new byte[2];
        new SecureRandom().nextBytes(raw);
        String id = "kid-" + Protocol.hex(raw);
        String code = Protocol.randomCode(16);

        String lan = Util.localIp();
        String wg = wgHost.getText().toString().trim();
        String host = wg.isEmpty() ? lan : lan + "+" + wg;

        Db.get(this).addDevice(id, n, code);
        final String pairing = Protocol.pairing(host, ControlServer.PORT, id, code);

        result.removeAllViews();

        LinearLayout card = Ui.card(this);
        card.addView(Ui.pill(this, "код привязки", Ui.BLUE, Ui.BLUE_SOFT));

        // Крупный QR: ребёнок сканирует его камерой агента — привязка без ручного ввода.
        try {
            android.widget.ImageView qr = new android.widget.ImageView(this);
            qr.setImageBitmap(qrBitmap(pairing));
            qr.setAdjustViewBounds(true);
            int side = Ui.dp(this, 240);
            qr.setLayoutParams(new LinearLayout.LayoutParams(side, side));
            qr.setBackgroundColor(0xFFFFFFFF);
            qr.setPadding(Ui.dp(this, 8), Ui.dp(this, 8), Ui.dp(this, 8), Ui.dp(this, 8));
            card.addView(qr, top(10));
            card.addView(Ui.txt(this, "Наведите камеру агента на этот код", 12,
                    Ui.MUTED, false), top(6));
        } catch (Exception ignored) {
            // Ручной ввод ниже остаётся запасным путём.
        }

        TextView codeView = Ui.txt(this, pairing, 15, Ui.INK, true);
        codeView.setTypeface(android.graphics.Typeface.MONOSPACE);
        codeView.setTextIsSelectable(true);
        codeView.setPadding(0, Ui.dp(this, 12), 0, Ui.dp(this, 4));
        card.addView(codeView);
        card.addView(Ui.txt(this, "Действует только для этого ребёнка", 12, Ui.MUTED, false));

        LinearLayout buttons = Ui.row(this);
        buttons.setPadding(0, Ui.dp(this, 12), 0, 0);
        buttons.addView(Ui.primary(this, "Копировать", new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                Ui.copy(PairingActivity.this, pairing);
                Ui.toast(PairingActivity.this, "Скопировано");
            }
        }), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        LinearLayout.LayoutParams ghostLp = new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        ghostLp.leftMargin = Ui.dp(this, 10);
        buttons.addView(Ui.ghost(this, "Готово", new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                finish();
            }
        }), ghostLp);
        card.addView(buttons);

        result.addView(card, top(18));

        if (!wg.isEmpty()) {
            LinearLayout note = Ui.card(this);
            note.addView(Ui.txt(this, "Два адреса", 14, Ui.INK, true));
            note.addView(Ui.txt(this, "Дома агент пойдёт по " + lan
                    + ", вне дома — по " + wg + ". Рабочий адрес запоминается автоматически.",
                    12.5f, Ui.INK2, false), top(6));
            result.addView(note, top(10));
        }
    }

    /** Renders the pairing string as a scannable QR image (white quiet zone included). */
    private android.graphics.Bitmap qrBitmap(String text) {
        boolean[][] m = QrCodec.encode(text);
        int scale = 6, quiet = 4, side = (QrCodec.SIZE + 2 * quiet) * scale;
        android.graphics.Bitmap bmp = android.graphics.Bitmap.createBitmap(
                side, side, android.graphics.Bitmap.Config.ARGB_8888);
        for (int y = 0; y < side; y++) {
            for (int x = 0; x < side; x++) {
                int mx = x / scale - quiet, my = y / scale - quiet;
                boolean dark = mx >= 0 && my >= 0 && mx < QrCodec.SIZE && my < QrCodec.SIZE
                        && m[my][mx];
                bmp.setPixel(x, y, dark ? 0xFF000000 : 0xFFFFFFFF);
            }
        }
        return bmp;
    }
}
