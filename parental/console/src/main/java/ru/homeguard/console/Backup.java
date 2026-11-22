package ru.homeguard.console;

import android.util.Base64;

import org.json.JSONArray;
import org.json.JSONObject;

import java.security.SecureRandom;

import javax.crypto.Cipher;
import javax.crypto.SecretKey;
import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.PBEKeySpec;
import javax.crypto.spec.SecretKeySpec;

/**
 * Portable, passphrase-encrypted backup: PBKDF2-SHA256 (150k) + AES-256-GCM.
 * The file is useless without the passphrase, and nothing leaves the phone.
 */
public final class Backup {

    private static final String MAGIC = "HGBAK1";
    private static final int ITERATIONS = 150_000;
    private static final int SALT = 16;
    private static final int IV = 12;

    private Backup() {}

    public static String create(Db db, String pass) throws Exception {
        if (pass == null || pass.length() < 6) {
            throw new IllegalArgumentException("пароль короче 6 символов");
        }
        JSONObject root = new JSONObject();
        root.put("v", 1);
        root.put("ts", System.currentTimeMillis() / 1000L);

        JSONArray devices = new JSONArray();
        for (Db.Device d : db.devices()) {
            JSONObject o = new JSONObject();
            o.put("id", d.id);
            o.put("name", d.name);
            o.put("code", d.secret);            // plaintext only inside the encrypted blob
            o.put("policy", d.policy);
            o.put("policy_v", d.policyV);
            o.put("last_seen", d.lastSeen);
            devices.put(o);
        }
        root.put("devices", devices);
        root.put("events", db.exportEvents(30));
        root.put("usage", db.exportUsage(60));

        return MAGIC + ":" + encrypt(pass, root.toString());
    }

    /** @return human summary: "2 детей, 340 событий, 120 записей". */
    public static String restore(Db db, String file, String pass) throws Exception {
        String text = file == null ? "" : file.trim();
        if (!text.startsWith(MAGIC + ":")) {
            throw new IllegalArgumentException("это не файл HomeGuard");
        }
        JSONObject root = new JSONObject(decrypt(pass, text.substring(MAGIC.length() + 1)));

        int devices = 0;
        JSONArray ds = root.optJSONArray("devices");
        for (int i = 0; ds != null && i < ds.length(); i++) {
            JSONObject o = ds.optJSONObject(i);
            if (o == null || o.optString("id", "").isEmpty()) continue;
            db.restoreDevice(o.optString("id"), o.optString("name", "Ребёнок"),
                    o.optString("code", ""), o.optJSONObject("policy"),
                    o.optInt("policy_v", 1), o.optLong("last_seen", 0));
            devices++;
        }

        int events = 0;
        JSONArray es = root.optJSONArray("events");
        for (int i = 0; es != null && i < es.length(); i++) {
            JSONArray row = es.optJSONArray(i);
            if (row == null || row.length() < 4) continue;
            db.restoreEvent(row.optString(0), row.optString(1), row.optString(2), row.optLong(3));
            events++;
        }

        int usage = 0;
        JSONArray us = root.optJSONArray("usage");
        for (int i = 0; us != null && i < us.length(); i++) {
            JSONArray row = us.optJSONArray(i);
            if (row == null || row.length() < 4) continue;
            db.restoreUsage(row.optString(0), row.optString(1), row.optString(2), row.optLong(3));
            usage++;
        }
        return devices + " детей, " + events + " событий, " + usage + " записей";
    }

    // ---------------- crypto ----------------

    private static String encrypt(String pass, String plain) throws Exception {
        byte[] salt = new byte[SALT];
        byte[] iv = new byte[IV];
        SecureRandom rnd = new SecureRandom();
        rnd.nextBytes(salt);
        rnd.nextBytes(iv);

        Cipher c = Cipher.getInstance("AES/GCM/NoPadding");
        c.init(Cipher.ENCRYPT_MODE, key(pass, salt), new GCMParameterSpec(128, iv));
        byte[] ct = c.doFinal(Protocol.utf8(plain));

        byte[] out = new byte[salt.length + iv.length + ct.length];
        System.arraycopy(salt, 0, out, 0, salt.length);
        System.arraycopy(iv, 0, out, salt.length, iv.length);
        System.arraycopy(ct, 0, out, salt.length + iv.length, ct.length);
        return Base64.encodeToString(out, Base64.NO_WRAP);
    }

    private static String decrypt(String pass, String body) throws Exception {
        byte[] all = Base64.decode(body, Base64.NO_WRAP);
        if (all.length <= SALT + IV) throw new IllegalArgumentException("файл повреждён");
        byte[] salt = new byte[SALT];
        byte[] iv = new byte[IV];
        byte[] ct = new byte[all.length - SALT - IV];
        System.arraycopy(all, 0, salt, 0, SALT);
        System.arraycopy(all, SALT, iv, 0, IV);
        System.arraycopy(all, SALT + IV, ct, 0, ct.length);

        Cipher c = Cipher.getInstance("AES/GCM/NoPadding");
        c.init(Cipher.DECRYPT_MODE, key(pass, salt), new GCMParameterSpec(128, iv));
        try {
            return new String(c.doFinal(ct), "UTF-8");
        } catch (javax.crypto.AEADBadTagException e) {
            throw new IllegalArgumentException("неверный пароль или файл повреждён");
        }
    }

    private static SecretKey key(String pass, byte[] salt) throws Exception {
        PBEKeySpec spec = new PBEKeySpec(pass.toCharArray(), salt, ITERATIONS, 256);
        try {
            SecretKeyFactory f = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256");
            return new SecretKeySpec(f.generateSecret(spec).getEncoded(), "AES");
        } finally {
            spec.clearPassword();
        }
    }
}
