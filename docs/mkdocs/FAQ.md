# FAQ

## Why can Blender-Launcher-V2 be flagged by antivirus?
Blender-Launcher-V2 is packaged with **PyInstaller**, which bundles Python, dependencies, and your code into a Windows executable. Some AV products may flag PyInstaller-built apps as suspicious due to **heuristics/ML detection** and “packed executable” patterns that are also used by malware. This is often a **false positive**, especially for new or low-download binaries.

Blender-Launcher-V2 is **open source on GitHub**, so you can review the code and/or build it yourself from source.

It's safe to whitelist the program in your antivirus software and report it as a false positive to your antivirus vendor.

## Why do I see a Windows security popup the first time I run it?
Windows may show a **SmartScreen / “Windows protected your PC”** prompt when an app is new, not widely downloaded, or **not code-signed**. This warning is typically about **publisher identity and reputation**, not proof the app is malicious.

To reduce these prompts, apps usually need **code signing** and time to build reputation through legitimate downloads.


## Where can I find the Blender Launcher log files?
Check the [Troubleshooting](troubleshooting.md#where-are-the-log-files) page for more information about log file locations.