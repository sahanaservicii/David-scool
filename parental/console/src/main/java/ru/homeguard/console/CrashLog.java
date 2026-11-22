package ru.homeguard.console;

import android.content.Context;
import android.os.Build;

import java.io.File;
import java.io.FileOutputStream;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

/**
 * Local crash log: the console runs unattended on the parent's phone, so a crash
 * must be visible later, without any crash-reporting service.
 */
public final class CrashLog {

    private static final String FILE = "crash.log";
    private static final long MAX = 64 * 1024;

    private CrashLog() {}

    public static void install(Context context) {
        final Context app = context.getApplicationContext();
        final Thread.UncaughtExceptionHandler previous =
                Thread.getDefaultUncaughtExceptionHandler();
        Thread.setDefaultUncaughtExceptionHandler(new Thread.UncaughtExceptionHandler() {
            @Override
            public void uncaughtException(Thread t, Throwable e) {
                try {
                    write(app, t, e);
                } catch (Throwable ignored) {}
                if (previous != null) previous.uncaughtException(t, e);
            }
        });
    }

    private static void write(Context c, Thread t, Throwable e) {
        StringWriter sw = new StringWriter();
        PrintWriter pw = new PrintWriter(sw);
        pw.println(new SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US).format(new Date()));
        pw.println("app " + c.getPackageName() + ", android " + Build.VERSION.RELEASE
                + " (sdk " + Build.VERSION.SDK_INT + "), device " + Build.MANUFACTURER
                + " " + Build.MODEL + ", thread " + t.getName());
        e.printStackTrace(pw);
        pw.flush();

        File f = new File(c.getFilesDir(), FILE);
        if (f.length() > MAX) {
            File old = new File(c.getFilesDir(), FILE + ".1");
            f.renameTo(old);
        }
        try (FileWriter w = new FileWriter(f, true)) {
            w.write(sw.toString());
            w.write("\n");
        } catch (Exception ignored) {}
    }

    /** Full log or null when nothing crashed yet. */
    public static String read(Context c) {
        File f = new File(c.getFilesDir(), FILE);
        if (!f.exists() || f.length() == 0) return null;
        try (java.io.FileInputStream in = new java.io.FileInputStream(f)) {
            byte[] buf = new byte[(int) f.length()];
            int n = in.read(buf);
            return new String(buf, 0, Math.max(0, n), "UTF-8");
        } catch (Exception e) {
            return null;
        }
    }

    public static void clear(Context c) {
        new File(c.getFilesDir(), FILE).delete();
        new File(c.getFilesDir(), FILE + ".1").delete();
    }

    /** Short one-line hint for the settings screen. */
    public static String summary(Context c) {
        File f = new File(c.getFilesDir(), FILE);
        if (!f.exists() || f.length() == 0) return "сбоев не было";
        return "есть запись · " + (f.length() / 1024 + 1) + " КБ";
    }

    static void appendRaw(Context c, String text) {
        try (FileOutputStream out = new FileOutputStream(new File(c.getFilesDir(), FILE), true)) {
            out.write(Protocol.utf8(text));
        } catch (Exception ignored) {}
    }
}
