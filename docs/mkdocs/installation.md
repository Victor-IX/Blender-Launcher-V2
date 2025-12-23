# Installation

## Installing Blender Launcher

1. Download the latest release for your **OS** from the [releases page](https://github.com/Victor-IX/Blender-Launcher-V2/releases/latest).
2. Unpack the `Blender Launcher.exe` file.
3. Run `Blender Launcher.exe`; for **Windows** users, you might get a security warning, just click on `More info` and then `Run anyway`.
4. Set your installation preferences, and set the [Library Folder](library_folder.md)
5. Enjoy!

!!! warning "Windows Users"

    Because the programs is built using [PyInstaller](https://github.com/pyinstaller/pyinstaller), your antivirus software may give a false positive warning. If that happens, you can whitelist the program in your antivirus software and report it as a false positive to your antivirus vendor.
    
    The false positives occur because some people use PyInstaller for malware and the only solution to not being flagged is to sign the executable with a code signing certificate (and this costs money 💸).
    

### For Archlinux Users

Install from AUR [blender-launcher-v2-bin](https://aur.archlinux.org/packages/blender-launcher-v2-bin)


## Updating Blender Launcher

### Manual update

1. Download latest release for your OS from the [releases page](https://github.com/Victor-IX/Blender-Launcher-V2/releases/latest)
2. Quit any running instance of **Blender Launcher**
3. Unpack the `Blender Launcher.exe` file and replace existing one.
4. You have succesfully updated. Enjoy!

### Automatic update

!!! warning "v1.15.1 and lower"
    Automatic updates are not available if you are using a version of the Blender Launcher prior to version `1.15.2`.
    To update, you need to do a manual update of Blender Launcher.

1. Press the `Update to version %.%.%` button in the right bottom corner of the window.
2. Blender Luancher will then begin downloading and extracting the new version.
3. Once this process is finished, wait for 5-30 seconds while the new version is configured.
4. Once update, Blender Launcher should automatically launch.
5. You have succesfully updated. Enjoy!

## Important Notes

!!! warning "Library Folder"

    It is recommended to create a new folder on a non system drive or inside a user folder like `Documents` to avoid any file collisions and to have a nice structure.

!!! warning "Windows Users"

    Don't use UAC protected folders like `Program Files` and don't run **Blender Launcher** with administrator rights. It can cause unexpected behavior in the  program itself as well as Blender 3D.

!!! info "Linux Users"

    - Make sure that the OS GLIBC version is 2.27 or higher, otherwise try to build **Blender Launcher** from source manually following the [Development](development.md) documentation page.
    - Consider installing the [TopIcons Plus](https://extensions.gnome.org/extension/1031/topicons/) extension for proper tray icon support.

!!! info "About AUR Packages"

    The AUR packages are based on this repo, but they are not maintained by core contributors of BLV2. 

!!! info "Blender Version Manager Users"

    Since **Blender Launcher** is written from scratch with a different concept in mind it is strongly recommended not to use a **Root Folder** as **Library Folder**. Otherwise delete all builds from **Root Folder** or move them to `%Library Folder%\daily` directory.
