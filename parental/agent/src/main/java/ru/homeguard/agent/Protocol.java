package ru.homeguard.agent;

import android.content.Context;

import org.json.JSONObject;

import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.Locale;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

/** Shared wire protocol helpers (mirrored in the console app). */
public final class Protocol {
    public static final String VERSION = "1";
    public static final String PATH_SYNC = "/api/v1/sync";
    public static final String PATH_ACK = "/api/v1/ack";
    public static final String PATH_PING = "/api/v1/ping";

    public static final String H_DEVICE = "X-HG-Device";
    public static final String H_TS = "X-HG-Ts";
    public static final String H_NONCE = "X-HG-Nonce";
    public static final String H_SIG = "X-HG-Sig";

    /** Method tag for server -> agent responses. */
    public static final String RESP = "RESP";

    private Protocol() {}

    public static byte[] utf8(String s) {
        try {
            return s.getBytes("UTF-8");
        } catch (Exception e) {
            return s.getBytes();
        }
    }

    public static String hex(byte[] raw) {
        StringBuilder sb = new StringBuilder(raw.length * 2);
        for (byte b : raw) sb.append(String.format(Locale.US, "%02x", b));
        return sb.toString();
    }

    public static String sha256(String s) {
        try {
            return hex(MessageDigest.getInstance("SHA-256").digest(utf8(s)));
        } catch (Exception e) {
            throw new IllegalStateException(e);
        }
    }

    public static String hmac(String secret, String msg) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(utf8(secret), "HmacSHA256"));
            return hex(mac.doFinal(utf8(msg)));
        } catch (Exception e) {
            throw new IllegalStateException(e);
        }
    }

    /** Signature covers method, path, timestamp, nonce and body hash. */
    public static String sign(String secret, String method, String path, String ts, String nonce, String body) {
        String canonical = method + "\n" + path + "\n" + ts + "\n" + nonce + "\n"
                + sha256(body == null ? "" : body);
        return hmac(secret, canonical);
    }

    /** Signature of a response body, bound to the request path. */
    public static String signResponse(String secret, String path, String ts, String nonce, String body) {
        return sign(secret, RESP, path, ts, nonce, body);
    }

    public static String nonce() {
        byte[] b = new byte[12];
        new SecureRandom().nextBytes(b);
        return hex(b);
    }

    public static String nowTs() {
        return String.valueOf(System.currentTimeMillis() / 1000L);
    }

    /** Base32 without ambiguous characters, used for pairing codes. */
    /** Length-independent comparison, no early exit on the first mismatch. */
    public static boolean constantTimeEquals(String a, String b) {
        if (a == null || b == null || a.length() != b.length()) return false;
        int r = 0;
        for (int i = 0; i < a.length(); i++) r |= a.charAt(i) ^ b.charAt(i);
        return r == 0;
    }

    public static String randomCode(int chars) {
        final String abc = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
        SecureRandom r = new SecureRandom();
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < chars; i++) {
            if (i > 0 && i % 4 == 0) sb.append('-');
            sb.append(abc.charAt(r.nextInt(abc.length())));
        }
        return sb.toString();
    }

    public static String normalizeCode(String code) {
        if (code == null) return null;
        return code.replace("-", "").replace(" ", "").trim().toUpperCase(Locale.US);
    }

    public static String toHex(byte[] data) {
        return hex(data);
    }

    public static JSONObject obj() {
        return new JSONObject();
    }

    /** Pairing payload: hg1:host:port:deviceId:code */
    public static String makePairing(String host, int port, String deviceId, String code) {
        return "hg1:" + host + ":" + port + ":" + deviceId + ":" + code;
    }
}
