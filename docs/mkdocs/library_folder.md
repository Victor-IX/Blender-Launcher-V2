the Library Folder is the directory on your hard drive where every build you download is stored.

!!! warning

    Don't create your **Library Folder** inside UAC protected folders like `Program Files` and don't run **Blender Launcher** with administrator rights. It is recommended to create a new directory on a non system drive or inside user folder like `Documents` to avoid any file collisions and have a nice structure. Doing otherwise can cause unexpected behavior in the program itself as well as Blender 3D.

## Changing Library Folder

On first launch Blender Launcher will ask for choosing **Library Folder**. After it can be changed in [Library Folder](settings.md#library-folder) section of [Settings Window](settings.md).

There is known issue related to Qt and some Linux distributions like Mint where it fails to show folder browser dialog window. To pass this issue it is possible to set **Library Folder** via command line arguments:

```bash
"path/to/Blender Launcher" -set-library-folder "<path>"
```

## Structure

**Library Folder** has the following structure:

```
.
└─ %Library Folder%
    ├─ bl_symlink
    ├─ .temp
    ├─ custom
    ├─ template
    └─ <a folder for every supported repo>
```
### Supported Repos

See [Blender Forks](blender_forks.md) for detailed information about the supported forks.

```
.
└─ %Library Folder%
    ├─ stable        # Official Blender stable releases
    ├─ daily         # Official Blender daily builds
    ├─ experimental  # Official Blender experimental branches
    ├─ bforartists   # Bforartists builds
    ├─ upbge-stable  # UPBGE stable releases
    ├─ upbge-weekly  # UPBGE weekly/alpha builds
    └─ custom        # Manual custom builds
```

### Special folders

#### `bl_symlink`

:   **bl_symlink** is a symbolic link that creates via [library build context menu](user_interface.md#library-build-context-menu).

#### `.temp`

:   **.temp** folder is used to store downloaded `*.zip` and `*.tar` files. They should be deleted once every download task is complete.

#### `custom`

:   **custom** folder is used to store builds downloaded by user manually (e.g. from [GraphicAll](https://blender.community/c/graphicall/)). To use custom builds with Blender Launcher they must be placed inside **custom** folder manually:

    ```
    .
    └─ %Library Folder%
        └─ custom
            ├─ %custom blender build 1%
            │   ├─ ...
            │   ├─ blender.exe
            │   └─ ...
            ├─ %custom blender build 2%
            │   ├─ ...
            │   ├─ blender.exe
            │   └─ ...
            └─ ...
    ```

#### `template`

:   **template** folder is used to store custom Blender preferences and scripts (e.g. [HEAVYPOLY config](https://github.com/HEAVYPOLY/HEAVYPOLY_Blender)). Template represents a file structure similar to one existing in Blender build (e.g. `blender-2.91.0-windows64\2.91`):

    ```
    .
    └─ %Library Folder%
        └─ template
            ├─ ...
            ├─ config
            ├─ datafiles
            ├─ scripts
            │   ├─ ...
            │   ├─ addons
            │   ├─ startup
            │   └─ ...
            └─...
    ```

    More detailed information available on Blender manual [Application Templates](https://docs.blender.org/manual/en/dev/advanced/app_templates.html) page.
