<style>body {text-align: justify}</style>

# Settings

## Settings Window

:   To open the **Settings Window**, use the button with a gear icon on the top left of the **Main Window**. All changes are saved automatically.

## General

![General page of Settings](imgs/settings_window_general.png)

### Application

#### Library Folder

:   **Library Folder** - a directory on the hard drive where all downloaded builds are stored.
    
:    For detailed information, check the [Library Folder](library_folder.md) page.

#### Launch When System Starts

!!! info
    This only works on Windows.

:   Determines if **Blender Launcher** will run when the system starts.

#### Show Tray Icon

:   Toggles the visibility of the tray icon. If the option is disabled, **Blender Launcher** will shut down after closing its **Main Window**.
If this option is enabled, to completely close the **Blender Launcher** you need to close it through its **tray icon** on the bottom right. The icon may be hidden under the arrow icon located to the left of the tray icon.

#### Launch Minimized To Tray

:   Determines if the **Main Window** will pop up when the user executes **Blender Launcher**, or only the tray icon will be shown.

#### Worker Thread Count

:   Sets the maximal number of **CPU Thread Blender** Launcher can use.

### File Association
:   Use the Blender Launcher as Default program to launch `.blend` files with the desired version
:   For detail information, check the [File Association](file_association.md) page.

#### Create Shortcut

:   TODO

#### Register File Association

:   Add Blender Launcher as the Default program to open `.blend`

#### Unregister File Association

:   Remove the Blender Launcher as the Default program to open `.blend`

#### Launch Time Duration

:   Set the time to automatically lunch a `.blend` file with the corresponding version

    !!! info
        Blend files will be automatically lunch after this timer if the correspond Blender version exist in the [Blender Launcher Library](library_folder.md)

    ```
    -1 -> No Timer (Require the user to click on launch)
     0 -> instant (Only if matching version exist)
     3 -> 3 Seconde (Will lunch after 3s if matching version exist)
    ```

### Advanced

#### Default Delete Action

: Define the default action for removing a build in the right-click menu.  
Default value: `Send to Trash`.

!!! info
    You can reverse the behavior of the button by pressing Shift in the right-click menu.

## Appearance

![Appearance page of Settings](imgs/settings_window_appearance.png)

### Window

#### Use System Title Bar

#### Enable High DPI Scaling

:   Determines if the **Blender Launcher** user interface will automatically scale based on the monitor's pixel density. To apply changes, the application should be restarted.

### Notifications

#### New Available Build

:   Show OS notifications when new builds of Blender are available in the Downloads tab.

#### Finished Downloading

:   Show OS notifications when a build finished downloading and is added to the Library tab.

#### Errors

:   Show OS notification when an error occurs on the Blender Launcher.

### Tabs

#### Default Tab

:   Set which tab will be opened when **Blender Launcher** starts.

#### Sync Library & Downloads

:   Determines if the pages of Library and Downloads tabs will be automatically matched with each other.

#### Default Library Page

:   Sets which page of the Library tab will be opened when **Blender Launcher** starts.

#### Default Downloads Page

:   Sets which page of the Downloads tab will be opened when **Blender Launcher** starts.

## Connection

![Connection page of Settings](imgs/settings_window_connection.png)

### Proxy

#### Use Custom TLS Certificates

:   Enables the use of custom TLS certificates for secure communication with the proxy server.

#### Type

:   Specifies the type of proxy server to connect to (e.g., HTTP, SOCKS).

#### IP

:   Specifies the IP address of the proxy server and port number through which Blender Launcher will connect to the proxy server.

#### Proxy User

:   Specifies the username required to authenticate with the proxy server, if applicable.

#### Password

:   Specifies the password required to authenticate with the proxy server, if applicable.

## Blender Builds

![Blender Builds page of Settings](imgs/settings_window_blenderbuilds.png)

### Visibility and Downloading

: Choose the visibility and build downloading for different Blender branches and repositories.

#### Eye

- Show / Hide Library tab (Also removes the link download tab)

#### Download

- Enable / Disable the scraping of builds. 
  
    !!! Info
        This helps reduce the number of requests the Blender Launcher creates on the Blender server for builds the user doesn't use.

### Checking For Builds

#### Check Automatically

:   Automatically check if a new build has been released and send a notification if there is a new one available.

#### On Startup

:   If Blender launcher will check for a new build when launched.

#### Min Stable Build to Scrape

:   Set the minimum Blender version to scrape; this reduces the request amount and speeds up the build gathering time.

#### Scrape Stable Builds

:   If the Blender Launcher will gather the Stable build, disabling this will speed up the gathering of the daily build.

#### Scrape Automated Builds

:   If the Blender Launcher will gather the automated daily build (daily, experimental, patch).

### Downloading & Saving build

Actions that will be performed on newly added builds to Library tab right after downloading is finished.

#### Mark As Favorite

:   Mark every newly added build to the Library tab as favorite depending on the branch type.

#### Install Template

:   Installs a template on newly added builds to the Library tab.

### Launching Builds

#### Quick Launch Global SHC

:   Launches builds added to quick launch via a user-defined key sequence.

#### Hide Console On Startup

!!! info
    This only works on Windows.

:   Launch Blender via `blender-launcher.exe` to hide the console on startup. Works on Blender version 3.0 and higher.

    !!! warning "Known Issues"

        When using this feature, the number of running instances will not be shown.

#### Startup Arguments

:   Adds specific instructions as if Blender were launching from the command line (after the blender executable i.e. `blender [args …]`).

:   For example, the `-W` (force opening Blender in fullscreen mode) argument internally will produce the following command:

    ```
    %path to blender executable% -W
    ```

:   List of commands can be found on Blender manual [Command Line Arguments](https://docs.blender.org/manual/en/latest/advanced/command_line/arguments.html) page.

#### Bash Arguments

!!! info
    This only works on Linux.

:   Adds specific instructions as if Blender were launching from the command line (before the blender executable i.e. `[args …] blender`).

:   For example, `env __NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia` (force Blender to use a dedicated graphics card) arguments internally will produce the following command:

    ```
    env __NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia nohup %path to blender executable% %startup arguments%
    ```
```