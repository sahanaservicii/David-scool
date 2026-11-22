package ru.homeguard.console;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.os.IBinder;

/** Hosts the embedded control server while the parent's phone is online. */
public class ConsoleService extends Service {

    private static final String CH_ID = "hg_console_srv";
    private static final int NOTIF = 2001;

    public static volatile boolean alive = false;
    private ControlServer server;

    public static void start(Context c) {
        try {
            Intent i = new Intent(c, ConsoleService.class);
            if (Build.VERSION.SDK_INT >= 26) c.startForegroundService(i);
            else c.startService(i);
        } catch (Exception ignored) {}
    }

    public static String status() {
        return alive ? "сервер работает" : "сервер остановлен";
    }

    @Override
    public void onCreate() {
        super.onCreate();
        NotificationManager nm = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
        if (nm != null) {
            nm.createNotificationChannel(new NotificationChannel(CH_ID, "HomeGuard консоль",
                    NotificationManager.IMPORTANCE_MIN));
        }
        startForeground(NOTIF, notif("запуск…"));
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (server == null) {
            server = new ControlServer(this);
            server.start();
        }
        alive = server.isRunning();
        String ip = Util.localIp();
        String text = alive
                ? "слушаю " + ip + ":" + ControlServer.PORT
                : "ошибка: " + server.lastError();
        NotificationManager nm = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
        if (nm != null) nm.notify(NOTIF, notif(text));
        return START_STICKY;
    }

    @Override
    public void onDestroy() {
        alive = false;
        if (server != null) server.stop();
        super.onDestroy();
    }

    private Notification notif(String text) {
        Intent open = new Intent(this, MainActivity.class);
        PendingIntent pi = PendingIntent.getActivity(this, 0, open,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        Notification.Builder b = Build.VERSION.SDK_INT >= 26
                ? new Notification.Builder(this, CH_ID) : new Notification.Builder(this);
        return b.setContentTitle("HomeGuard Консоль")
                .setContentText(text)
                .setSmallIcon(android.R.drawable.stat_sys_upload_done)
                .setOngoing(true)
                .setShowWhen(false)
                .setContentIntent(pi)
                .build();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
