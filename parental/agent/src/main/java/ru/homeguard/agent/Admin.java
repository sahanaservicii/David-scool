package ru.homeguard.agent;

import android.app.admin.DevicePolicyManager;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.os.Build;
import android.os.UserManager;
import android.provider.Settings;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Applies a policy document through DevicePolicyManager. Every step is guarded. */
public final class Admin {

    public static final String ACTION_LOCK_STATE = "ru.homeguard.agent.LOCK_STATE";

    private Admin() {}

    public static DevicePolicyManager dpm(Context c) {
        return (DevicePolicyManager) c.getSystemService(Context.DEVICE_POLICY_SERVICE);
    }

    public static ComponentName cn(Context c) {
        return new ComponentName(c, GuardReceiver.class);
    }

    public static boolean isOwner(Context c) {
        try {
            return dpm(c).isDeviceOwnerApp(c.getPackageName());
        } catch (Exception e) {
            return false;
        }
    }

    public static boolean isAdmin(Context c) {
        try {
            return dpm(c).isAdminActive(cn(c));
        } catch (Exception e) {
            return false;
        }
    }

    /** Adds/clears a single user restriction without touching the others. */
    private static void restriction(Context c, String key, boolean allowed, JSONObject out) {
        try {
            if (allowed) dpm(c).clearUserRestriction(cn(c), key);
            else dpm(c).addUserRestriction(cn(c), key);
        } catch (Exception e) {
            put(out, key, e.getClass().getSimpleName());
        }
    }

    public static JSONObject apply(Context c, JSONObject p) {
        JSONObject res = new JSONObject();
        JSONObject errors = new JSONObject();
        try {
            res.put("v", p.optInt("v", 0));
        } catch (Exception ignored) {}

        if (!isOwner(c)) {
            try {
                res.put("ok", false);
                res.put("error", "not_device_owner");
            } catch (Exception ignored) {}
            return res;
        }

        // Feature toggles: true = allowed, false = blocked by policy.
        Map<String, String> restrictions = new LinkedHashMap<>();
        restrictions.put("install_apps", UserManager.DISALLOW_INSTALL_APPS);
        restrictions.put("install_unknown", UserManager.DISALLOW_INSTALL_UNKNOWN_SOURCES_GLOBALLY);
        restrictions.put("uninstall_apps", UserManager.DISALLOW_UNINSTALL_APPS);
        restrictions.put("wifi_config", UserManager.DISALLOW_CONFIG_WIFI);
        restrictions.put("bluetooth", UserManager.DISALLOW_BLUETOOTH);
        restrictions.put("usb", UserManager.DISALLOW_USB_FILE_TRANSFER);
        restrictions.put("safe_boot", UserManager.DISALLOW_SAFE_BOOT);
        restrictions.put("factory_reset", UserManager.DISALLOW_FACTORY_RESET);
        restrictions.put("add_user", UserManager.DISALLOW_ADD_USER);
        restrictions.put("config_vpn", UserManager.DISALLOW_CONFIG_VPN);
        restrictions.put("debug", UserManager.DISALLOW_DEBUGGING_FEATURES);
        restrictions.put("apps_control", UserManager.DISALLOW_APPS_CONTROL);
        restrictions.put("config_date", UserManager.DISALLOW_CONFIG_DATE_TIME);
        restrictions.put("user_switch", UserManager.DISALLOW_USER_SWITCH);
        restrictions.put("share_location", UserManager.DISALLOW_SHARE_LOCATION);

        for (Map.Entry<String, String> e : restrictions.entrySet()) {
            if (p.has(e.getKey())) restriction(c, e.getValue(), p.optBoolean(e.getKey(), true), errors);
        }

        try {
            dpm(c).setCameraDisabled(cn(c), !p.optBoolean("camera", true));
        } catch (Exception e) {
            put(errors, "camera", e.getClass().getSimpleName());
        }
        try {
            dpm(c).setScreenCaptureDisabled(cn(c), !p.optBoolean("screen_capture", true));
        } catch (Exception e) {
            put(errors, "screen_capture", e.getClass().getSimpleName());
        }
        try {
            dpm(c).setStatusBarDisabled(cn(c), !p.optBoolean("status_bar", true));
        } catch (Exception e) {
            put(errors, "status_bar", e.getClass().getSimpleName());
        }
        try {
            dpm(c).setKeyguardDisabled(cn(c), !p.optBoolean("keyguard", true));
        } catch (Exception e) {
            put(errors, "keyguard", e.getClass().getSimpleName());
        }
        try {
            if (p.has("password_quality")) {
                int q = p.optInt("password_quality", DevicePolicyManager.PASSWORD_QUALITY_SOMETHING);
                dpm(c).setPasswordQuality(cn(c), q);
            }
        } catch (Exception e) {
            put(errors, "password_quality", e.getClass().getSimpleName());
        }

        applyBlockedApps(c, p, errors);
        applyKiosk(c, p, errors);

        if (p.optBoolean("grant_permissions", true)) {
            grantPermission(c, android.Manifest.permission.ACCESS_FINE_LOCATION);
            grantPermission(c, android.Manifest.permission.ACCESS_COARSE_LOCATION);
            grantPermission(c, android.Manifest.permission.POST_NOTIFICATIONS);
        }

        // Cache the applied document so the scheduler keeps working offline.
        Store.put(c, "policy", p.toString());
        Store.putInt(c, "policy_v", p.optInt("v", 0));

        try {
            res.put("ok", true);
            res.put("errors", errors);
        } catch (Exception ignored) {}
        return res;
    }

    private static void applyBlockedApps(Context c, JSONObject p, JSONObject errors) {
        JSONArray arr = p.optJSONArray("blocked");
        List<String> now = new ArrayList<>();
        if (arr != null) {
            for (int i = 0; i < arr.length(); i++) {
                String pkg = arr.optString(i, "");
                if (pkg.contains(".") && !pkg.equals(c.getPackageName())) now.add(pkg);
            }
        }
        String prevRaw = Store.get(c, "blocked_prev", "");
        List<String> prev = new ArrayList<>();
        for (String s : prevRaw.split(",")) if (!s.isEmpty()) prev.add(s);

        for (String pkg : prev) {
            if (!now.contains(pkg)) {
                try {
                    dpm(c).setPackagesSuspended(cn(c), new String[]{pkg}, false);
                } catch (Exception ignored) {}
                try {
                    dpm(c).setApplicationHidden(cn(c), pkg, false);
                } catch (Exception ignored) {}
            }
        }
        for (String pkg : now) {
            try {
                dpm(c).setPackagesSuspended(cn(c), new String[]{pkg}, true);
            } catch (Exception e) {
                put(errors, "suspend:" + pkg, e.getClass().getSimpleName());
            }
            if (p.optBoolean("hide_blocked", false)) {
                try {
                    dpm(c).setApplicationHidden(cn(c), pkg, true);
                } catch (Exception ignored) {}
            }
        }
        Store.put(c, "blocked_prev", join(now));
    }

    private static void applyKiosk(Context c, JSONObject p, JSONObject errors) {
        JSONObject k = p.optJSONObject("kiosk");
        try {
            if (k != null && k.optBoolean("enabled", false)) {
                List<String> pkgs = new ArrayList<>();
                pkgs.add(c.getPackageName());
                String launcher = launcherPackage(c);
                if (launcher != null && !pkgs.contains(launcher)) pkgs.add(launcher);
                JSONArray arr = k.optJSONArray("packages");
                if (arr != null) {
                    for (int i = 0; i < arr.length(); i++) {
                        String pkg = arr.optString(i, "");
                        if (pkg.contains(".") && !pkgs.contains(pkg)) pkgs.add(pkg);
                    }
                }
                dpm(c).setLockTaskPackages(cn(c), pkgs.toArray(new String[0]));
                dpm(c).setLockTaskFeatures(cn(c), DevicePolicyManager.LOCK_TASK_FEATURE_NONE);
                Store.put(c, "kiosk", join(pkgs));
            } else {
                dpm(c).setLockTaskPackages(cn(c), new String[]{c.getPackageName()});
                Store.put(c, "kiosk", "");
            }
        } catch (Exception e) {
            put(errors, "kiosk", e.getClass().getSimpleName());
        }
    }

    public static String launcherPackage(Context c) {
        try {
            Intent i = new Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_HOME);
            ResolveInfo ri = c.getPackageManager().resolveActivity(i, PackageManager.MATCH_DEFAULT_ONLY);
            return ri == null || ri.activityInfo == null ? null : ri.activityInfo.packageName;
        } catch (Exception e) {
            return null;
        }
    }

    public static void grantPermission(Context c, String perm) {
        try {
            dpm(c).setPermissionGrantState(cn(c), c.getPackageName(), perm,
                    DevicePolicyManager.PERMISSION_GRANT_STATE_GRANTED);
        } catch (Exception ignored) {}
    }

    public static void lockNow(Context c) {
        try {
            dpm(c).lockNow();
        } catch (Exception ignored) {}
    }

    public static void setAirplane(Context c, boolean on) {
        try {
            dpm(c).setGlobalSetting(cn(c), Settings.Global.AIRPLANE_MODE_ON, on ? "1" : "0");
            Intent i = new Intent(Intent.ACTION_AIRPLANE_MODE_CHANGED);
            i.putExtra("state", on);
            c.sendBroadcast(i);
        } catch (Exception ignored) {}
    }

    private static void put(JSONObject o, String k, String v) {
        try {
            o.put(k, v);
        } catch (Exception ignored) {}
    }

    public static String join(List<String> list) {
        StringBuilder sb = new StringBuilder();
        for (String s : list) {
            if (sb.length() > 0) sb.append(',');
            sb.append(s);
        }
        return sb.toString();
    }

    public static String androidVersion() {
        return Build.VERSION.RELEASE == null ? "?" : Build.VERSION.RELEASE;
    }
}
