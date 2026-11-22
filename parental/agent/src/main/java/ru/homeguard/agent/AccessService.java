package ru.homeguard.agent;

import android.accessibilityservice.AccessibilityService;
import android.view.accessibility.AccessibilityEvent;

import org.json.JSONArray;
import org.json.JSONObject;

/**
 * Optional enforcement layer: catches app switches to blocked packages
 * and closes them even when the app was launched from a notification or link.
 */
public class AccessService extends AccessibilityService {

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        if (event == null || event.getEventType() != AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED) return;
        CharSequence pkgCs = event.getPackageName();
        if (pkgCs == null) return;
        String pkg = pkgCs.toString();

        if (LockState.locked && !pkg.equals(getPackageName())) {
            CurfewActivity.show(this, LockState.reason);
            return;
        }
        if (pkg.equals(getPackageName())) return;

        JSONObject policy = Scheduler.policy(this);
        if (policy == null) return;
        JSONArray blocked = policy.optJSONArray("blocked");
        if (blocked == null) return;
        for (int i = 0; i < blocked.length(); i++) {
            if (pkg.equals(blocked.optString(i, ""))) {
                performGlobalAction(GLOBAL_ACTION_HOME);
                Event.push(this, "blocked", pkg);
                return;
            }
        }
    }

    @Override
    public void onInterrupt() {
    }
}
