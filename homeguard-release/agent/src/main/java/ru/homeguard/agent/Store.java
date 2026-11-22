package ru.homeguard.agent;

import android.content.Context;
import android.content.SharedPreferences;
import android.os.Build;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;

import java.security.KeyStore;
import java.security.SecureRandom;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

/**
 * Agent configuration. The shared secret is sealed with an Android Keystore AES-GCM key,
 * never written to disk in clear text.
 */
public final class Store {
    private static final String PREF = "hg_agent";
    private static final String ALIAS = "hg_agent_secret";
    private static final String K_SEC = "secret_sealed";

    private Store() {}

    public static SharedPreferences prefs(Context c) {
        return c.getSharedPreferences(PREF, Context.MODE_PRIVATE);
    }

    public static String get(Context c, String key, String def) {
        return prefs(c).getString(key, def);
    }

    public static void put(Context c, String key, String value) {
        prefs(c).edit().putString(key, value).apply();
    }

    public static int getInt(Context c, String key, int def) {
        return prefs(c).getInt(key, def);
    }

    public static void putInt(Context c, String key, int value) {
        prefs(c).edit().putInt(key, value).apply();
    }

    public static long getLong(Context c, String key, long def) {
        return prefs(c).getLong(key, def);
    }

    public static void putLong(Context c, String key, long value) {
        prefs(c).edit().putLong(key, value).apply();
    }

    public static String serverUrl(Context c) {
        String s = get(c, "server", null);
        return s == null ? null : s.trim();
    }

    /** Ordered endpoint list: LAN first, then WireGuard (or vice versa). */
    public static java.util.List<String> servers(Context c) {
        java.util.List<String> out = new java.util.ArrayList<>();
        String multi = get(c, "servers", null);
        if (multi != null) {
            for (String s : multi.split(",")) {
                String t = s.trim();
                if (!t.isEmpty() && !out.contains(t)) out.add(t);
            }
        }
        if (out.isEmpty()) {
            String one = serverUrl(c);
            if (one != null && !one.trim().isEmpty()) out.add(one.trim());
        }
        return out;
    }

    public static void setServers(Context c, java.util.List<String> list) {
        StringBuilder sb = new StringBuilder();
        for (String s : list) {
            if (s == null || s.trim().isEmpty()) continue;
            if (sb.length() > 0) sb.append(',');
            sb.append(s.trim());
        }
        put(c, "servers", sb.toString());
        put(c, "server", list.isEmpty() ? null : list.get(0));
        put(c, "server_active", null);
    }

    public static String deviceId(Context c) {
        String id = get(c, "device_id", null);
        if (id == null) {
            id = "agent-" + Protocol.hex(random(5));
            put(c, "device_id", id);
        }
        return id;
    }

    public static String deviceName(Context c) {
        String n = get(c, "device_name", null);
        return n == null ? (Build.MANUFACTURER + " " + Build.MODEL) : n;
    }

    public static boolean paired(Context c) {
        return serverUrl(c) != null && secret(c) != null;
    }

    public static void setSecret(Context c, String secret) throws Exception {
        byte[] iv = new byte[12];
        new SecureRandom().nextBytes(iv);
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.ENCRYPT_MODE, key(), new GCMParameterSpec(128, iv));
        byte[] ct = cipher.doFinal(Protocol.utf8(Protocol.normalizeCode(secret)));
        String sealed = Base64.encodeToString(iv, Base64.NO_WRAP) + ":" + Base64.encodeToString(ct, Base64.NO_WRAP);
        prefs(c).edit().putString(K_SEC, sealed).apply();
    }

    public static String secret(Context c) {
        String sealed = prefs(c).getString(K_SEC, null);
        if (sealed == null) return null;
        try {
            String[] parts = sealed.split(":");
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.DECRYPT_MODE, key(), new GCMParameterSpec(128, Base64.decode(parts[0], Base64.NO_WRAP)));
            byte[] pt = cipher.doFinal(Base64.decode(parts[1], Base64.NO_WRAP));
            return new String(pt, "UTF-8");
        } catch (Exception e) {
            return null;
        }
    }

    private static SecretKey key() throws Exception {
        KeyStore ks = KeyStore.getInstance("AndroidKeyStore");
        ks.load(null);
        if (ks.containsAlias(ALIAS)) {
            return (SecretKey) ks.getKey(ALIAS, null);
        }
        KeyGenerator kg = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore");
        kg.init(new KeyGenParameterSpec.Builder(ALIAS,
                KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .build());
        return kg.generateKey();
    }

    private static byte[] random(int n) {
        byte[] b = new byte[n];
        new SecureRandom().nextBytes(b);
        return b;
    }
}
