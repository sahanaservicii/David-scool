package ru.homeguard.console;

import android.app.Application;

/** Process-wide setup: crash log and daily database housekeeping. */
public class App extends Application {

    @Override
    public void onCreate() {
        super.onCreate();
        CrashLog.install(this);
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    Db.get(App.this).prune();
                } catch (Throwable ignored) {}
            }
        }, "hg-prune").start();
    }
}
