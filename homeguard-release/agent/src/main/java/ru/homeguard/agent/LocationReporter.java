package ru.homeguard.agent;

import android.Manifest;
import android.content.Context;
import android.content.pm.PackageManager;
import android.location.Location;
import android.location.LocationManager;
import android.os.Build;

import org.json.JSONObject;

/** One-shot location read for the "locate" command. No background tracking unless requested. */
public final class LocationReporter {

    private LocationReporter() {}

    public static JSONObject oneShot(Context c) {
        JSONObject out = new JSONObject();
        try {
            if (c.checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED
                    && c.checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
                out.put("error", "no_permission");
                return out;
            }
            LocationManager lm = (LocationManager) c.getSystemService(Context.LOCATION_SERVICE);
            if (lm == null) {
                out.put("error", "no_service");
                return out;
            }
            Location best = null;
            for (String p : new String[]{LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER}) {
                try {
                    Location l = lm.getLastKnownLocation(p);
                    if (l != null && (best == null || l.getTime() > best.getTime())) best = l;
                } catch (Exception ignored) {}
            }
            if (best != null) {
                out.put("lat", best.getLatitude());
                out.put("lon", best.getLongitude());
                out.put("acc", Math.round(best.getAccuracy()));
                out.put("ts", best.getTime() / 1000L);
                out.put("age_min", (System.currentTimeMillis() - best.getTime()) / 60000L);
            } else {
                out.put("error", "no_fix");
            }
        } catch (Exception e) {
            try {
                out.put("error", e.getClass().getSimpleName());
            } catch (Exception ignored) {}
        }
        return out;
    }

    public static String providerHint(Context c) {
        LocationManager lm = (LocationManager) c.getSystemService(Context.LOCATION_SERVICE);
        if (lm == null) return "-";
        StringBuilder sb = new StringBuilder();
        try {
            if (lm.isProviderEnabled(LocationManager.GPS_PROVIDER)) sb.append("gps ");
        } catch (Exception ignored) {}
        try {
            if (lm.isProviderEnabled(LocationManager.NETWORK_PROVIDER)) sb.append("net");
        } catch (Exception ignored) {}
        return sb.toString().trim();
    }

    public static String sdk() {
        return Build.VERSION.SDK_INT >= 33 ? "13+" : String.valueOf(Build.VERSION.SDK_INT);
    }
}
