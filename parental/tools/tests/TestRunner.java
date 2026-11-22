import java.lang.reflect.Method;
import java.util.HashSet;
import java.util.Set;

/**
 * Offline tests for the wire protocol. No JUnit, no network: both copies of
 * Protocol (agent and console) are loaded and cross-checked against each other
 * and against published vectors.
 *
 * Run: sh tools/test.sh
 */
public final class TestRunner {

    private static int passed;
    private static int failed;

    public static void main(String[] args) throws Exception {
        Class<?> con = Class.forName("ru.homeguard.console.Protocol");
        Class<?> agt = Class.forName("ru.homeguard.agent.Protocol");

        // --- published vectors ---
        eq("sha256(\"abc\")", "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
                call(con, "sha256", "abc"));
        eq("sha256(\"abc\") agent", call(con, "sha256", "abc"), call(agt, "sha256", "abc"));
        eq("hmac RFC4231 #2", "5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843",
                call(con, "hmac", "Jefe", "what do ya want for nothing?"));
        eq("hmac agent == console",
                call(con, "hmac", "Jefe", "what do ya want for nothing?"),
                call(agt, "hmac", "Jefe", "what do ya want for nothing?"));

        // --- signatures must match between the two apps ---
        String secret = "K7QM4ZP2XW9RTB6N";
        String[][] cases = {
                {"POST", "/api/v1/sync", "1763300000", "2f8c1d4a9b7e3c5d6a1b2c3d4e5f6071", "{\"a\":1}"},
                {"POST", "/api/v1/sync", "1763300001", "00000000000000000000000000000000", ""},
                {"GET", "/api/v1/ping", "1763300002", "ffffffffffffffffffffffffffffffff", null},
                {"POST", "/api/v1/ack", "1763300003", "abcdefabcdefabcdefabcdefabcdefab", "{\"id\":\"x\"}"},
        };
        for (String[] c : cases) {
            String a = (String) call(con, "sign", secret, c[0], c[1], c[2], c[3], c[4]);
            String b = (String) call(agt, "sign", secret, c[0], c[1], c[2], c[3], c[4]);
            eq("sign " + c[0] + " " + c[1], a, b);
            check("sign is 64 hex chars", a.matches("[0-9a-f]{64}"));
        }

        // --- a signature must depend on every field ---
        String base = (String) call(con, "sign", secret, "POST", "/api/v1/sync",
                "1763300000", "n1", "{\"a\":1}");
        check("body changes signature", !base.equals(call(con, "sign", secret, "POST",
                "/api/v1/sync", "1763300000", "n1", "{\"a\":2}")));
        check("ts changes signature", !base.equals(call(con, "sign", secret, "POST",
                "/api/v1/sync", "1763300001", "n1", "{\"a\":1}")));
        check("nonce changes signature", !base.equals(call(con, "sign", secret, "POST",
                "/api/v1/sync", "1763300000", "n2", "{\"a\":1}")));
        check("secret changes signature", !base.equals(call(con, "sign", "other", "POST",
                "/api/v1/sync", "1763300000", "n1", "{\"a\":1}")));
        eq("null body == empty body",
                call(con, "sign", secret, "POST", "/api/v1/sync", "1763300000", "n1", ""),
                call(con, "sign", secret, "POST", "/api/v1/sync", "1763300000", "n1", null));

        // --- response signatures (console -> agent) ---
        String r1 = (String) call(con, "signResponse", secret, "/api/v1/sync",
                "1763300000", "n1", "{\"ok\":true}");
        String r2 = (String) call(agt, "signResponse", secret, "/api/v1/sync",
                "1763300000", "n1", "{\"ok\":true}");
        eq("response sign console == agent", r1, r2);
        check("response signature is 64 hex", r1.matches("[0-9a-f]{64}"));
        check("response bound to path", !r1.equals(call(con, "signResponse", secret,
                "/api/v1/ack", "1763300000", "n1", "{\"ok\":true}")));
        check("response differs from request", !r1.equals(base));
        String cn = (String) call(con, "nonce");
        check("console nonce is 24 hex", cn.matches("[0-9a-f]{24}"));

        // --- pairing strings ---
        String pc = (String) call(con, "pairing", "192.168.1.5+192.168.9.2", 8787, "kid-1a2b", "ABCD-EFGH");
        String pa = (String) call(agt, "makePairing", "192.168.1.5+192.168.9.2", 8787, "kid-1a2b", "ABCD-EFGH");
        eq("pairing console == agent", pc, pa);
        eq("pairing format", "hg1:192.168.1.5+192.168.9.2:8787:kid-1a2b:ABCD-EFGH", pc);

        // --- codes ---
        eq("normalize console", "ABCD1234", call(con, "normalizeCode", " ab-cd 12 34 "));
        eq("normalize agent", "ABCD1234", call(agt, "normalizeCode", " ab-cd-12-34 "));
        check("constant time equal", (Boolean) call(con, "constantTimeEquals", "abc", "abc"));
        check("constant time differs", !((Boolean) call(con, "constantTimeEquals", "abc", "abd")));
        check("constant time null", !((Boolean) call(con, "constantTimeEquals", null, "abc")));

        // --- agent helpers ---
        Set<String> nonces = new HashSet<>();
        boolean nonceShape = true;
        for (int i = 0; i < 500; i++) {
            String n = (String) call(agt, "nonce");
            if (n.length() != 24 || !n.matches("[0-9a-f]{24}")) nonceShape = false;
            nonces.add(n);
        }
        check("nonce is 24 hex chars", nonceShape);
        eq("nonces are unique", 500, nonces.size());
        long ts = Long.parseLong((String) call(agt, "nowTs"));
        check("nowTs is current", Math.abs(System.currentTimeMillis() / 1000L - ts) < 5);

        String code = (String) call(con, "randomCode", 16);
        check("code has 16 chars", code.replace("-", "").length() == 16);
        check("code charset", code.replace("-", "").matches("[A-Z2-9]+"));

        System.out.println();
        System.out.println(passed + " passed, " + failed + " failed");
        if (failed > 0) System.exit(1);
        System.out.println("PROTOCOL OK");
    }

    private static Object call(Class<?> c, String name, Object... args) throws Exception {
        Method m = null;
        for (Method x : c.getDeclaredMethods()) {
            if (x.getName().equals(name) && x.getParameterCount() == args.length) {
                m = x;
                break;
            }
        }
        if (m == null) throw new NoSuchMethodException(c.getName() + "." + name + "/" + args.length);
        return m.invoke(null, args);
    }

    private static void eq(String what, Object expected, Object actual) {
        if (expected == null ? actual == null : expected.equals(actual)) {
            passed(what);
        } else {
            fail(what + "\n    ожидалось: " + expected + "\n    получено:  " + actual);
        }
    }

    private static void check(String what, boolean ok) {
        if (ok) passed(what);
        else fail(what);
    }

    private static void passed(String what) {
        passed++;
        System.out.println("  ok   " + what);
    }

    private static void fail(String what) {
        failed++;
        System.out.println("  FAIL " + what);
    }
}
