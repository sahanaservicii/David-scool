/*
 * Minimal QR codec for HomeGuard pairing strings.
 * Fixed: version 5 (37x37), byte mode, error correction level L, mask 0.
 * No external dependencies, Java 8+. Public domain-style, written for this project.
 */
package ru.homeguard.console;

import java.nio.charset.StandardCharsets;

public final class QrCodec {
    public static final int SIZE = 37;              // version 5
    private static final int DATA_CODEWORDS = 108;  // version 5, level L
    private static final int EC_CODEWORDS = 26;     // version 5, level L, 1 block
    private static final int CENTER = SIZE - 7;     // alignment pattern center (30,30)
    private static final int GF_EXP[] = new int[512];
    private static final int GF_LOG[] = new int[256];
    private static int[] GEN;
    private static boolean[][] FUNCTION;

    static {
        int x = 1;
        for (int i = 0; i < 255; i++) {
            GF_EXP[i] = x;
            GF_LOG[x] = i;
            x <<= 1;
            if ((x & 0x100) != 0) x ^= 0x11D;
        }
        for (int i = 255; i < 512; i++) GF_EXP[i] = GF_EXP[i - 255];
        GEN = genPoly(EC_CODEWORDS);
    }

    private static int gfMul(int a, int b) {
        return (a == 0 || b == 0) ? 0 : GF_EXP[GF_LOG[a] + GF_LOG[b]];
    }

    private static int[] genPoly(int degree) {
        int[] result = new int[degree];
        result[degree - 1] = 1;
        int root = 1;
        for (int i = 0; i < degree; i++) {
            for (int j = 0; j < degree; j++) {
                result[j] = gfMul(result[j], root);
                if (j + 1 < degree) result[j] ^= result[j + 1];
            }
            root = gfMul(root, 2);
        }
        return result;
    }

    private static boolean bit(int x, int i) {
        return ((x >>> i) & 1) != 0;
    }

    private static int formatBits(int ecMask) {
        int rem = ecMask;
        for (int i = 0; i < 10; i++) rem = (rem << 1) ^ (((rem >>> 9) & 1) * 0x537);
        return ((ecMask << 10) | rem) ^ 0x5412;
    }

    private static void set(boolean[][] m, int x, int y, boolean v) {
        m[y][x] = v;
        FUNCTION[y][x] = true;
    }

    private static void drawFinder(boolean[][] m, int left, int top) {
        for (int dy = -1; dy <= 7; dy++) {
            for (int dx = -1; dx <= 7; dx++) {
                int x = left + dx, y = top + dy;
                if (x < 0 || y < 0 || x >= SIZE || y >= SIZE) continue;
                boolean dark = dx >= 0 && dx <= 6 && dy >= 0 && dy <= 6
                        && (dx == 0 || dx == 6 || dy == 0 || dy == 6
                        || (dx >= 2 && dx <= 4 && dy >= 2 && dy <= 4));
                set(m, x, y, dark);
            }
        }
    }

    /** Draws all function patterns and fills FUNCTION; does not touch data modules. */
    private static void drawFunction(boolean[][] m) {
        FUNCTION = new boolean[SIZE][SIZE];
        drawFinder(m, 0, 0);
        drawFinder(m, SIZE - 7, 0);
        drawFinder(m, 0, SIZE - 7);
        for (int i = 8; i <= SIZE - 9; i++) {
            set(m, i, 6, i % 2 == 0);
            set(m, 6, i, i % 2 == 0);
        }
        for (int dy = -2; dy <= 2; dy++) {
            for (int dx = -2; dx <= 2; dx++) {
                int d = Math.max(Math.abs(dx), Math.abs(dy));
                set(m, CENTER + dx, CENTER + dy, d != 1);
            }
        }
        set(m, 8, SIZE - 8, true); // dark module
        int f = formatBits(0b01000); // level L (01), mask 0 (000)
        for (int i = 0; i <= 5; i++) set(m, 8, i, bit(f, i));
        set(m, 8, 7, bit(f, 6));
        set(m, 8, 8, bit(f, 7));
        set(m, 7, 8, bit(f, 8));
        for (int i = 9; i < 15; i++) set(m, 14 - i, 8, bit(f, i));
        for (int i = 0; i < 8; i++) set(m, SIZE - 1 - i, 8, bit(f, i));
        for (int i = 8; i < 15; i++) set(m, 8, SIZE - 15 + i, bit(f, i));
    }

    private static void append(boolean[] bits, int pos, int value, int len) {
        for (int i = 0; i < len; i++) bits[pos + i] = bit(value, len - 1 - i);
    }

    private static int readInt(boolean[] bits, int pos, int len) {
        int v = 0;
        for (int i = 0; i < len; i++) v = (v << 1) | (bits[pos + i] ? 1 : 0);
        return v;
    }

    private static void place(boolean[][] m, byte[] data, int[] ecc) {
        byte[] all = new byte[data.length + ecc.length];
        System.arraycopy(data, 0, all, 0, data.length);
        for (int i = 0; i < ecc.length; i++) all[data.length + i] = (byte) ecc[i];
        int k = 0;
        for (int right = SIZE - 1; right >= 1; right -= 2) {
            if (right == 6) right = 5;
            for (int vert = 0; vert < SIZE; vert++) {
                for (int j = 0; j < 2; j++) {
                    int x = right - j;
                    boolean upward = ((right + 1) & 2) == 0;
                    int y = upward ? SIZE - 1 - vert : vert;
                    if (!FUNCTION[y][x] && k < all.length * 8) {
                        m[y][x] = bit(all[k >>> 3] & 0xFF, 7 - (k & 7));
                        k++;
                    }
                }
            }
        }
    }

    /** Returns a 37x37 boolean matrix; true = dark module. */
    public static boolean[][] encode(String text) {
        byte[] bytes = text.getBytes(StandardCharsets.UTF_8);
        if (bytes.length > DATA_CODEWORDS - 2) {
            throw new IllegalArgumentException("pairing string too long for QR");
        }
        boolean[] bits = new boolean[DATA_CODEWORDS * 8];
        int p = 0;
        append(bits, p, 0x4, 4); p += 4;            // byte mode
        append(bits, p, bytes.length, 8); p += 8;   // character count
        for (byte b : bytes) { append(bits, p, b & 0xFF, 8); p += 8; }
        int term = Math.min(4, bits.length - p);
        p += term;
        while (p % 8 != 0) p++;
        int pad = 0xEC;
        while (p < bits.length) { append(bits, p, pad, 8); p += 8; pad ^= (0xEC ^ 0x11); }
        byte[] data = new byte[DATA_CODEWORDS];
        for (int i = 0; i < data.length; i++) {
            int v = 0;
            for (int j = 0; j < 8; j++) v = (v << 1) | (bits[i * 8 + j] ? 1 : 0);
            data[i] = (byte) v;
        }
        int[] ints = new int[data.length];
        for (int i = 0; i < data.length; i++) ints[i] = data[i] & 0xFF;
        int[] ecc = new int[EC_CODEWORDS];
        for (int b : ints) {
            int factor = b ^ ecc[0];
            System.arraycopy(ecc, 1, ecc, 0, EC_CODEWORDS - 1);
            ecc[EC_CODEWORDS - 1] = 0;
            for (int j = 0; j < EC_CODEWORDS; j++) ecc[j] ^= gfMul(GEN[j], factor);
        }
        boolean[][] m = new boolean[SIZE][SIZE];
        drawFunction(m);
        place(m, data, ecc);
        for (int y = 0; y < SIZE; y++) {
            for (int x = 0; x < SIZE; x++) {
                if (!FUNCTION[y][x] && (x + y) % 2 == 0) m[y][x] = !m[y][x];
            }
        }
        return m;
    }

    /** Decodes an already sampled 37x37 matrix. Returns null if format/mode is wrong. */
    public static String decode(boolean[][] m) {
        boolean[][] dummy = new boolean[SIZE][SIZE];
        drawFunction(dummy);
        boolean[][] u = new boolean[SIZE][SIZE];
        for (int y = 0; y < SIZE; y++) {
            for (int x = 0; x < SIZE; x++) {
                u[y][x] = m[y][x];
                if (!FUNCTION[y][x] && (x + y) % 2 == 0) u[y][x] = !u[y][x];
            }
        }
        boolean[] bits = new boolean[DATA_CODEWORDS * 8];
        int k = 0;
        for (int right = SIZE - 1; right >= 1; right -= 2) {
            if (right == 6) right = 5;
            for (int vert = 0; vert < SIZE; vert++) {
                for (int j = 0; j < 2; j++) {
                    int x = right - j;
                    boolean upward = ((right + 1) & 2) == 0;
                    int y = upward ? SIZE - 1 - vert : vert;
                    if (!FUNCTION[y][x] && k < bits.length) {
                        bits[k] = u[y][x];
                        k++;
                    }
                }
            }
        }
        if (readInt(bits, 0, 4) != 4) return null;
        int len = readInt(bits, 4, 8);
        if (len <= 0 || len > DATA_CODEWORDS - 2) return null;
        byte[] out = new byte[len];
        for (int i = 0; i < len; i++) out[i] = (byte) readInt(bits, 12 + i * 8, 8);
        return new String(out, StandardCharsets.UTF_8);
    }

    // ---------------------------------------------------------------- camera
    // Finds the three finder patterns, restores the module grid with an affine
    // transform, then feeds the 37x37 matrix to decode(). Pure Java, no OpenCV.

    private static final class Pt {
        float x, y;
        Pt(float x, float y) { this.x = x; this.y = y; }
    }

    /** Finds all 1:1:3:1:1 finder centers on one row (x coordinates). */
    private static void findersOnRow(byte[] g, int w, int y, java.util.List<Float> out) {
        int[] runs = new int[512];
        boolean[] dark = new boolean[512];
        int runCount = 0;
        boolean cur = (g[y * w] & 0xFF) < 128;
        int len = 0;
        for (int i = 0; i < w; i++) {
            boolean v = (g[y * w + i] & 0xFF) < 128;
            if (v == cur) len++;
            else {
                if (runCount < runs.length) { runs[runCount] = len; dark[runCount] = cur; }
                runCount++;
                cur = v; len = 1;
            }
        }
        if (runCount < runs.length) { runs[runCount] = len; dark[runCount] = cur; }
        runCount++;
        for (int i = 0; i + 4 < runCount; i++) {
            if (!dark[i] || dark[i + 1] || !dark[i + 2] || dark[i + 3] || !dark[i + 4]) continue;
            float s = (runs[i] + runs[i + 1] + runs[i + 3] + runs[i + 4]) / 4f;
            if (s < 2 || s > 40) continue;
            if (runs[i + 2] < 2.3f * s || runs[i + 2] > 3.7f * s) continue;
            if (runs[i] < 0.5f * s || runs[i] > 1.7f * s) continue;
            if (runs[i + 1] < 0.5f * s || runs[i + 1] > 1.7f * s) continue;
            if (runs[i + 3] < 0.5f * s || runs[i + 3] > 1.7f * s) continue;
            if (runs[i + 4] < 0.5f * s || runs[i + 4] > 1.7f * s) continue;
            int start = 0;
            for (int j = 0; j <= i + 1; j++) start += runs[j];
            out.add(start + runs[i + 2] / 2f);
            i += 4;
        }
    }

    /** Decodes a QR directly from a grayscale camera frame (1 byte per pixel). */
    public static String decodeImage(byte[] g, int w, int h) {
        java.util.List<Pt> pts = new java.util.ArrayList<>();
        java.util.List<Float> xs = new java.util.ArrayList<>();
        for (int y = 2; y < h - 2; y += 2) {
            xs.clear();
            findersOnRow(g, w, y, xs);
            for (Float cx : xs) pts.add(new Pt(cx, y));
        }
        if (pts.size() < 6) return null;
        // Cluster nearby detections (same finder seen on several rows).
        java.util.List<Pt> centers = new java.util.ArrayList<>();
        boolean[] used = new boolean[pts.size()];
        for (int i = 0; i < pts.size(); i++) {
            if (used[i]) continue;
            java.util.List<Float> cxs = new java.util.ArrayList<>();
            java.util.List<Float> cys = new java.util.ArrayList<>();
            for (int j = i; j < pts.size(); j++) {
                if (used[j]) continue;
                if (Math.abs(pts.get(j).x - pts.get(i).x) < 40
                        && Math.abs(pts.get(j).y - pts.get(i).y) < 36) {
                    used[j] = true;
                    cxs.add(pts.get(j).x); cys.add(pts.get(j).y);
                }
            }
            if (cxs.size() >= 2) {
                java.util.Collections.sort(cxs);
                java.util.Collections.sort(cys);
                centers.add(new Pt(cxs.get(cxs.size() / 2), cys.get(cys.size() / 2)));
            }
        }
        if (centers.size() < 3) return null;
        // TL finder = smallest x+y; TR = largest x; BL found geometrically below.
        Pt tl = centers.get(0), tr = centers.get(0);
        for (Pt c : centers) {
            if (c.x + c.y < tl.x + tl.y) tl = c;
        }
        for (Pt c : centers) {
            if (c != tl && c.x > tr.x) tr = c;
        }
        if (tr == tl) return null;
        // BL is perpendicular to TL->TR at the same distance (finder centers form
        // a right isosceles triangle). Pick the cluster closest to that point.
        float ex = tl.x - (tr.y - tl.y);
        float ey = tl.y + (tr.x - tl.x);
        Pt bl = null;
        float nearer = Float.MAX_VALUE;
        for (Pt c : centers) {
            if (c == tl || c == tr) continue;
            float d = (c.x - ex) * (c.x - ex) + (c.y - ey) * (c.y - ey);
            if (d < nearer) { nearer = d; bl = c; }
        }
        if (bl == null) return null;
        // Affine transform: finder centers are 30 modules apart; map src offsets
        // from the TL center onto the frame using the TL->TR and TL->BL vectors.
        float dx1 = (tr.x - tl.x) / 30f, dy1 = (tr.y - tl.y) / 30f;
        float dx2 = (bl.x - tl.x) / 30f, dy2 = (bl.y - tl.y) / 30f;
        // Try a few thresholds and polarity to survive poor lighting/auto-exposure.
        for (int th : new int[]{128, 96, 160, 72, 184}) {
            for (int inv = 0; inv < 2; inv++) {
                boolean[][] m = new boolean[SIZE][SIZE];
                for (int my = 0; my < SIZE; my++) {
                    for (int mx = 0; mx < SIZE; mx++) {
                        float u = mx - 3f, v = my - 3f;            // module offset from TL finder center
                        int ix = Math.round(tl.x + u * dx1 + v * dx2);
                        int iy = Math.round(tl.y + u * dy1 + v * dy2);
                        boolean dark = ix >= 0 && iy >= 0 && ix < w && iy < h
                                && (g[iy * w + ix] & 0xFF) < th;
                        m[my][mx] = inv == 0 ? dark : !dark;
                    }
                }
                String r = decode(m);
                if (r != null) return r;
            }
        }
        return null;
    }

    private QrCodec() {}
}
