# Troubleshooting

## First steps

**Before creating an issue, please check the following:**

* Avoid duplicates - look through [open](https://github.com/Victor-IX/Blender-Launcher-V2/issues) and [closed](https://github.com/Victor-IX/Blender-Launcher-V2/issues?q=is%3Aissue+is%3Aclosed) issues sections and make sure your problem is not reported by another user

* Make sure you're using the latest build of Blender Launcher from [releases](https://github.com/Victor-IX/Blender-Launcher-V2/releases)

* If Blender 3D is closing right after running it from Blender Launcher, the problem is probably in the build itself or in [configuration files](https://docs.blender.org/manual/en/2.83/advanced/blender_directory_layout.html)

* For general questions go to [Blender Artists thread](https://blenderartists.org/t/blender-launcher-standalone-software-client) or our [Discord](https://discord.gg/3jrTZFJkTd)

## Log file
Blender Launcher keeps a log file named `Blender Launcher.log`.
=== "Windows"
    The log file can be found in the **LocalAppdata** folder:
    ```
    %localappdata%/Blender Launcher/
    ```
=== "Linux"
    The log file can be found in the **.cache** folder:
    ```
    ~/.cache/Blender Launcher/
    ```
=== "MacOS"
    The log file can be found in the **Library** folder:
    ```
    ~/Library/Logs/Blender Launcher/
    ```

## Blender Launcher debug mode

Blender Launcher logs warnings and errors into `Blender Launcher.log` by default. To retrieve additional useful debug information use `-debug` flag:

!!! warning "Close Blender Launcher"

    Before executing the command, you need to completely close Blender Launcher. On **Windows**, by default the program is running as a **tray icon** and can be closed through the **bottom right icon**. For more info, check [Tray Icon Documentation](settings.md#show-tray-icon).

!!! info "Log file"

    The **log file** can be found in the **LocalAppdata** folder on **Windows**
    `%localappdata%/Blender Launcher/`

=== "Windows CMD"

    ```
    .\"Blender Launcher.exe" -debug
    ```

=== "Linux"

    ```
    ./Blender\ Launcher -debug
    ```

    * On Linux it is possible to retrieve useful debug information using following command:

        ```
        gdb ./Blender\ Launcher
        run
        ```

## How to report a bug

To report a bug, use an [issue template](https://github.com/Victor-IX/Blender-Launcher-V2/issues/new?assignees=Victor-IX&labels=bug&template=bug_report.md&title=). Consider attaching the [Blender Launcher.log](#log-file) file.

[:fontawesome-solid-bug: Submit an issue](https://github.com/Victor-IX/Blender-Launcher-V2/issues/new?assignees=Victor-IX&labels=bug&template=bug_report.md&title=){: .md-button .md-button--primary }
