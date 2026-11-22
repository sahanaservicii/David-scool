package ru.homeguard.agent;

import android.app.admin.DeviceAdminReceiver;
import android.content.Context;
import android.content.Intent;

/** Receives device-admin lifecycle events. */
public class GuardReceiver extends DeviceAdminReceiver {

    @Override
    public void onEnabled(Context context, Intent intent) {
        Store.put(context, "admin_enabled_at", String.valueOf(System.currentTimeMillis()));
        SyncService.start(context);
    }

    @Override
    public void onDisabled(Context context, Intent intent) {
        Store.put(context, "admin_disabled_at", String.valueOf(System.currentTimeMillis()));
    }

    @Override
    public void onLockTaskModeEntering(Context context, Intent intent, String pkg) {
        Store.put(context, "locktask_pkg", pkg == null ? "" : pkg);
    }

    @Override
    public void onLockTaskModeExiting(Context context, Intent intent) {
        Store.put(context, "locktask_pkg", "");
    }
}
