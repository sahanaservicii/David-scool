package ru.homeguard.agent;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/** Minimal HTTP client (no third-party deps, no redirects, explicit timeouts). */
public final class Http {

    public static final class Resp {
        public final int code;
        public final String body;
        private final Map<String, String> headers;

        Resp(int code, String body, Map<String, String> headers) {
            this.code = code;
            this.body = body;
            this.headers = headers;
        }

        public boolean ok() {
            return code >= 200 && code < 300;
        }

        /** Response header by name, case-insensitive. */
        public String header(String name) {
            return name == null ? null : headers.get(name.toLowerCase(Locale.ROOT));
        }
    }

    private Http() {}

    public static Resp post(String url, Map<String, String> headers, String body, int connectMs, int readMs) {
        HttpURLConnection c = null;
        try {
            c = (HttpURLConnection) new URL(url).openConnection();
            c.setConnectTimeout(connectMs);
            c.setReadTimeout(readMs);
            c.setRequestMethod("POST");
            c.setInstanceFollowRedirects(false);
            c.setUseCaches(false);
            c.setDoOutput(true);
            c.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            c.setRequestProperty("Accept", "application/json");
            c.setRequestProperty("Connection", "close");
            if (headers != null) {
                for (Map.Entry<String, String> e : headers.entrySet()) {
                    c.setRequestProperty(e.getKey(), e.getValue());
                }
            }
            byte[] payload = (body == null ? "" : body).getBytes(StandardCharsets.UTF_8);
            c.setFixedLengthStreamingMode(payload.length);
            try (OutputStream os = c.getOutputStream()) {
                os.write(payload);
            }
            int code = c.getResponseCode();
            Map<String, String> rh = headers(c);
            InputStream is = code >= 400 ? c.getErrorStream() : c.getInputStream();
            return new Resp(code, readAll(is), rh);
        } catch (Exception e) {
            return new Resp(-1, e.getClass().getSimpleName() + ": " + e.getMessage(),
                    new HashMap<String, String>());
        } finally {
            if (c != null) c.disconnect();
        }
    }

    private static Map<String, String> headers(HttpURLConnection c) {
        Map<String, String> out = new HashMap<>();
        try {
            for (Map.Entry<String, List<String>> e : c.getHeaderFields().entrySet()) {
                if (e.getKey() == null || e.getValue() == null || e.getValue().isEmpty()) continue;
                out.put(e.getKey().toLowerCase(Locale.ROOT), e.getValue().get(0));
            }
        } catch (Exception ignored) {}
        return out;
    }

    public static Resp get(String url, int connectMs, int readMs) {
        HttpURLConnection c = null;
        try {
            c = (HttpURLConnection) new URL(url).openConnection();
            c.setConnectTimeout(connectMs);
            c.setReadTimeout(readMs);
            c.setRequestMethod("GET");
            c.setUseCaches(false);
            c.setRequestProperty("Connection", "close");
            int code = c.getResponseCode();
            Map<String, String> rh = headers(c);
            InputStream is = code >= 400 ? c.getErrorStream() : c.getInputStream();
            return new Resp(code, readAll(is), rh);
        } catch (Exception e) {
            return new Resp(-1, e.getClass().getSimpleName() + ": " + e.getMessage(),
                    new HashMap<String, String>());
        } finally {
            if (c != null) c.disconnect();
        }
    }

    private static String readAll(InputStream is) {
        if (is == null) return "";
        try (InputStream in = is; ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] buf = new byte[4096];
            int n;
            int total = 0;
            while ((n = in.read(buf)) > 0) {
                total += n;
                if (total > 512 * 1024) break;
                out.write(buf, 0, n);
            }
            return out.toString("UTF-8");
        } catch (Exception e) {
            return "";
        }
    }
}
