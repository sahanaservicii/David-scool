package ru.homeguard.agent;

import android.app.job.JobInfo;
import android.app.job.JobParameters;
import android.app.job.JobScheduler;
import android.app.job.JobService;
import android.content.ComponentName;
import android.content.Context;

/** Restarts the sync service if the system killed it, at most every 15 minutes. */
public class WatchdogJob extends JobService {

    private static final int JOB_ID = 4711;

    public static void schedule(Context c) {
        try {
            JobScheduler js = (JobScheduler) c.getSystemService(Context.JOB_SCHEDULER_SERVICE);
            if (js == null) return;
            JobInfo job = new JobInfo.Builder(JOB_ID, new ComponentName(c, WatchdogJob.class))
                    .setPeriodic(15 * 60 * 1000L)
                    .setPersisted(true)
                    .setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY)
                    .build();
            js.schedule(job);
        } catch (Exception ignored) {}
    }

    @Override
    public boolean onStartJob(JobParameters params) {
        SyncService.start(this);
        jobFinished(params, false);
        return false;
    }

    @Override
    public boolean onStopJob(JobParameters params) {
        return true;
    }
}
