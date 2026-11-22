package ru.homeguard.console;

import android.content.Context;
import android.content.SharedPreferences;
import android.net.wifi.WifiManager;
import android.text.format.Formatter;

import java.net.Inet4Address;
import java.net.InetAddress;
import java.net.NetworkInterface;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashSet;

public final class Util {

    private Util() {}

    public static SharedPreferences prefs(Context c) {
        return c.getSharedPreferences("hg_console", Context.MODE_PRIVATE);
    }

    /** Every usable IPv4 address: LAN first, then tunnel/VPN. */
    public static java.util.List<String> localIps() {
        java.util.LinkedHashSet<String> out = new java.util.LinkedHashSet<>();
        try {
            for (NetworkInterface ni : Collections.list(NetworkInterface.getNetworkInterfaces())) {
                if (!ni.isUp() || ni.isLoopback()) continue;
                for (InetAddress a : Collections.list(ni.getInetAddresses())) {
                    if (a instanceof Inet4Address && !a.isLoopbackAddress()) out.add(a.getHostAddress());
                }
            }
        } catch (Exception ignored) {}
        return new ArrayList<>(out);
    }

    /** Best LAN IPv4 address, used both in the UI and for pairing. */
    public static String localIp() {
        try {
            for (NetworkInterface ni : Collections.list(NetworkInterface.getNetworkInterfaces())) {
                if (!ni.isUp() || ni.isLoopback()) continue;
                String n = ni.getName();
                if (!n.startsWith("wlan") && !n.startsWith("eth")) continue;
                for (InetAddress a : Collections.list(ni.getInetAddresses())) {
                    if (a instanceof Inet4Address && !a.isLoopbackAddress()) {
                        return a.getHostAddress();
                    }
                }
            }
            for (NetworkInterface ni : Collections.list(NetworkInterface.getNetworkInterfaces())) {
                if (!ni.isUp() || ni.isLoopback()) continue;
                for (InetAddress a : Collections.list(ni.getInetAddresses())) {
                    if (a instanceof Inet4Address && !a.isLoopbackAddress()) return a.getHostAddress();
                }
            }
        } catch (Exception ignored) {}
        return "0.0.0.0";
    }

    public static String wifiName(Context c) {
        try {
            WifiManager wm = (WifiManager) c.getApplicationContext().getSystemService(Context.WIFI_SERVICE);
            if (wm == null || wm.getConnectionInfo() == null) return "?";
            String ssid = wm.getConnectionInfo().getSSID();
            return ssid == null ? "?" : ssid.replace("\"", "");
        } catch (Exception e) {
            return "?";
        }
    }

    public static String ago(long tsSec) {
        if (tsSec <= 0) return "никогда";
        long d = System.currentTimeMillis() / 1000L - tsSec;
        if (d < 60) return d + " с назад";
        if (d < 3600) return (d / 60) + " мин назад";
        if (d < 86400) return (d / 3600) + " ч назад";
        return (d / 86400) + " дн назад";
    }
}
