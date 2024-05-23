<style>body {text-align: justify}</style>

# Installation

## Installing Blender Launcher

1. Download latest release for your OS from [releases page](https://github.com/Victor-IX/Blender-Launcher-V2/releases/latest)
2. Unpack `Blender Launcher.exe` file and place it somewhere on your drive
3. Run `Blender Launcher.exe` file
4. If this is a first launch, program will ask for choosing [Library Folder](library_folder.md)
5. Enjoy!

### For Archlinux Users

Install from AUR [blender-launcher-bin](https://aur.archlinux.org/packages/blender-launcher-bin) or [blender-launcher-git](https://aur.archlinux.org/packages/blender-launcher-git) for experimental features


## Updating Blender Launcher

### Manual update

1. Download latest release for your OS from [releases page](https://github.com/Victor-IX/Blender-Launcher-V2/releases/latest)
2. Quit running instance of **Blender Launcher**
3. Unpack `Blender Launcher.exe` file and replace existing one
4. Enjoy!

### Automatic update

!!! warning "v1.15.1 and lower"
    Automatic updates are not available if you are using a version of the blender launcher prior to the `1.15.2` version.
    To update, you need to do a manual update of the blender launcher.

1. Press the `Update to version %.%.%` button on the right bottom corner
2. Wait until downloading and extracting process is finished
3. Wait for ~5-30 second while new version is configured and automatically launched
4. Enjoy!

## Important Notes

!!! warning "Library Folder"

    It is recommended to create a new folder on a non system drive or inside user folder like `Documents` to avoid any file collisions and have a nice structure.

!!! warning "Windows Users"

    Don't use UAC protected folders like `Program Files` and don't run **Blender Launcher** with administration rights. It may cause unexpected behavior for program itself as well as Blender 3D.

!!! info "Linux Users"

    - Make sure that OS GLIBC version is 2.27 or higher otherwise try to build **Blender Launcher** from source manually following [Development](development.md) documentation page.
    - Consider installing [TopIcons Plus](https://extensions.gnome.org/extension/1031/topicons/) extension for proper tray icon support.

!!! info "About AUR Packages"

    - The AUR packages are based on this repo, but they are not maintained by core contributors of BLV2. 

!!! info "Blender Version Manager Users"

    Since **Blender Launcher** is written from scratch with a different concept in mind it is strongly recommended not to use a **Root Folder** as **Library Folder**. Otherwise delete all builds from **Root Folder** or move them to `%Library Folder%\daily` directory.
