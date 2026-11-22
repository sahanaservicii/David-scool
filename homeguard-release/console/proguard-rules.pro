# Console: no reflection, no custom XML views.
-keep class ru.homeguard.console.MainActivity { *; }
-keep class ru.homeguard.console.ConsoleService { *; }
-keep class ru.homeguard.console.BootReceiver { *; }

-dontwarn org.json.**

-keepattributes SourceFile,LineNumberTable
-renamesourcefileattribute SourceFile
