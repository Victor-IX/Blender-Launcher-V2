<style>body {text-align: justify}</style>

# Installation

## Installing Blender Launcher

1. Download the latest release for your OS from the [releases page](https://github.com/Victor-IX/Blender-Launcher-V2/releases/latest).
2. Unpack the `Blender Launcher.exe` file and place it somewhere on your drive.
3. Run `Blender Launcher.exe`.
4. If this is a first launch, the program will ask you to choose [Library Folder](library_folder.md)
5. Enjoy!

### For Archlinux Users

Install from AUR [blender-launcher-bin](https://aur.archlinux.org/packages/blender-launcher-bin) or [blender-launcher-git](https://aur.archlinux.org/packages/blender-launcher-git) for experimental features


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

    Don't use UAC protected folders like `Program Files` and don't run **Blender Launcher** with administration rights. It may cause unexpected behavior for program itself as well as Blender 3D.

!!! info "Linux Users"

    - Make sure that OS GLIBC version is 2.27 or higher otherwise try to build **Blender Launcher** from source manually following [Development](development.md) documentation page.
    - Consider installing [TopIcons Plus](https://extensions.gnome.org/extension/1031/topicons/) extension for proper tray icon support.

!!! info "About AUR Packages"

    - The AUR packages are based on this repo, but they are not maintained by core contributors of BLV2. 

!!! info "Blender Version Manager Users"

    Since **Blender Launcher** is written from scratch with a different concept in mind it is strongly recommended not to use a **Root Folder** as **Library Folder**. Otherwise delete all builds from **Root Folder** or move them to `%Library Folder%\daily` directory.
