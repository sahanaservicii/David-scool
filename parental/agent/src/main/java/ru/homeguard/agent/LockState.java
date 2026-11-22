package ru.homeguard.agent;

/** Process-wide lock state, read by the curfew overlay and the sync service. */
public final class LockState {
    public static volatile boolean locked = false;
    public static volatile String reason = "";

    private LockState() {}

    public static void lock(String why) {
        reason = why == null ? "" : why;
        locked = true;
    }

    public static void unlock() {
        reason = "";
        locked = false;
    }
}
