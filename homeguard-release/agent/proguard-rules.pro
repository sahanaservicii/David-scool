# No reflection and no XML-inflated custom views: default AGP rules are enough.
# Keep the device-admin and accessibility entry points explicit for clarity.
-keep class ru.homeguard.agent.GuardReceiver { *; }
-keep class ru.homeguard.agent.AccessService { *; }
-keep class ru.homeguard.agent.BootReceiver { *; }
-keep class ru.homeguard.agent.SyncService { *; }

# JSON is parsed through android.jar; silence optional desugaring warnings.
-dontwarn org.json.**

# Readable crash reports: keep source file/line metadata.
-keepattributes SourceFile,LineNumberTable
-renamesourcefileattribute SourceFile
