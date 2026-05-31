# Installation

!!! warning "If you are upgrading from Blender Version Manager:"

    Since **Blender Launcher** is written from scratch with a different concept in mind it is strongly recommended not to use a **Root Folder** as **Library Folder**. Otherwise delete all builds from **Root Folder** or move them to `%Library Folder%\daily` directory.

## Installing Blender Launcher

### From [GitHub](https://github.com/Victor-IX/Blender-Launcher-V2/):

1. Download the latest release for your **OS** from the [releases page](https://github.com/Victor-IX/Blender-Launcher-V2/releases/latest).
2. Unpack the `Blender Launcher.exe` file.
3. Run `Blender Launcher.exe`
   
    for **Windows** or **MacOS** users, you might get a security warning, just click on `More info` and then `Run anyway`.[^err]

4. Set your installation preferences, and set the [Library Folder](library_folder.md)
5. Enjoy!

### From the AUR: [^aur]

Install from AUR [blender-launcher-v2-bin](https://aur.archlinux.org/packages/blender-launcher-v2-bin)


## Updating Blender Launcher

### Manual update

1. Download latest release for your OS from the [releases page](https://github.com/Victor-IX/Blender-Launcher-V2/releases/latest)
2. Quit any running instance of **Blender Launcher**
3. Unpack the `Blender Launcher` executable and replace the existing one.
4. You have succesfully updated. Enjoy!

### Automatic update[^prior-to-1.15.2]


1. Press the `Update to version %.%.%` button in the right bottom corner of the window.
2. Blender Launcher will then begin downloading and extracting the new version.
3. Once this process is finished, wait for 5-30 seconds while the new version is configured.
4. Once update, Blender Launcher should automatically launch.
5. You have succesfully updated. Enjoy!

!!! info "Linux Users"

    - Make sure that the OS GLIBC version is 2.27 or higher, otherwise try to build **Blender Launcher** from source manually following the [Development](development.md) documentation page.
    - Consider installing the [TopIcons Plus](https://extensions.gnome.org/extension/1031/topicons/) extension for proper tray icon support.



[^err]:

    Because the programs is built using PyInstaller, your antivirus software may give a false positive warning. See [FAQ](FAQ.md#why-can-blender-launcher-v2-be-flagged-by-antivirus) for more.

[^aur]: 
    The AUR packages are based on this repo, but they are not maintained by core contributors of BLV2. It may be out of date.

[^prior-to-1.15.2]:
    Automatic updates are not available if you are using a version of the Blender Launcher prior to version `1.15.2`.

    To update, you need to do a manual update of Blender Launcher.
