# User Interface

## Main Window

The **Main Window** is the main interface of Blender Launcher and where you can access all of the main features.

??? image "Menu Bar"

    <figure>
      <img src="../imgs/menu_bar.png"/>
      <figcaption>The menu bar</figcaption>
    </figure>

The top horizontal menu bar contains following buttons from left to right:

1. Settings Menu
2. Documentation
3. Minimize to taskbar
4. Minimize to tray

**Main Window** layout consists of three main tabs with corresponding pages:

* **Library** - list of local builds ready to use
    * **Stable**
    * **Daily**
    * **Experimental**
    * **Bforartists**
    * **UPBGE**
    * **UPBGE Weekly**
* **Downloads** - list of available official builds
    * **Stable**
    * **Daily**
    * **Experimental**
    * **Bforartists**
    * **UPBGE**
    * **UPBGE Weekly**
* **User** - list of favorite and custom builds defined by user
    * **Favorites**
    * **Custom**

!!! tip

    Use ++"Scroll Wheel"++ while hovering tabs to quickly switch between them.

!!! note

    By default Library and Downloads pages will be automatically matched between each over. To change this behavior toggle [Sync Library & Downloads Pages](settings.md#sync-library-downloads) checkbox in settings.

The bottom status bar shows following information from left to right:

1. Status of application
2. Blender Launcher version number

## Library Tab

??? image "Screenshots"

    <figure>
      <img src="../imgs/library_daily.png"/>
      <figcaption>Library Tab, Daily Page</figcaption>
    </figure>

Library tab is a place where all local builds are shown based on category. Each category contains a list of items which represents a build information. Library build item shows following information from left to right:

1. Launch button

    !!! note

        Play icon :fontawesome-solid-play: on the right side of button indicates that build set to [quick launch](#add-to-quick-launch).

2. Version number including subversion or phase (Alpha, Beta)
3. Branch name
4. Date and time of build commit target

    !!! note

        Take in mind that [builder.blender.org](https://builder.blender.org/download/) shows when build was uploaded to server.

    !!! tip

        ++"Left Button"++ click on date and time label will show hash number and vice versa.

5. Number of running instances / new build indicator

!!! tip

    ++"2x Left Button"++ click on library build item will automatically launch build.

### Library Build Context Menu

??? image "Screenshots"

    <figure>
      <img src="../imgs/library_context_menu.png"/>
      <figcaption>Library Build Context Menu</figcaption>
    </figure>

Build context menu can be accessed via right click on build item.

### Open previous file

:   Open the last closed file

#### Add To Quick Launch

:   Sets selected build to be accessed from tray icon context menu.

#### Add To Favorites

:   Add selected build to Favorites page of User tab.

### Debug

:   Multiple option to investigate and debug the program

#### Register Extension [Windows only]

:   Silently register blend-file extension (show thumbnails in file explorer and use selected build as default to open `*.blend` files).

    !!! warning "Known Issues"

        Registering may fail if `*.blend` files not already associated with Blender or associated with different unrelated application.

#### Create Shortcut

:   Create shortcut for selected build on desktop.

#### Create Symlink

:   Create [symbolic link](https://en.wikipedia.org/wiki/Symbolic_link) for selected build pointing to `%Library Folder%/blender_symlink`.

#### Install Template

:   Install template for selected build (check [template](library_folder.md#template) for more details).

#### Show Release Notes [Stable and LTS builds only]

:   Reveal page with release notes for the selected build in a web browser.

#### Show Folder

:   Reveal the folder containing the selected build in the system file explorer.

### Edit Build

:   Edit the build info used to display the installed build.

#### Delete From Drive

:   Delete the selected build from the drive and remove it from the Blender Launcher.

## Downloads Tab

??? image "Screenshots"

    <figure>
      <img src="../imgs/downloads_experimental.png"/>
      <figcaption>Downloads Tab, Experimental Page</figcaption>
    </figure>

Downloads tab is a place where all available official builds are shown based on category. Each category contains a list of items which represents a build information. Downloadable build item shows following information from left to right:

1. Download button
2. Version number including subversion or phase (Alpha, Beta)
3. Branch name
4. Upload date and time of build to server

    !!! tip

        ++"Left Button"++ click on date and time label will show hash number and vice versa.

5. New build indicator

!!! tip

    ++"2x Left Button"++ click on downloadable build item will automatically start downloading.

### Download Build Context Menu

Build context menu can be accessed via right click on build item.

#### Show Release Notes [Stable and LTS builds only]

:   Reveal page with release notes for selected build in web browser.

## User Tab

User tab is a place where favorite and custom builds can be defined.

### Favorites Page

??? image "Screenshots"

    <figure>
      <img src="../imgs/user_favorites.png"/>
      <figcaption>User Tab, Favorites Page</figcaption>
    </figure>

Favorites page contains builds added from Library tab using context menu `Add To Favorites` action. It has the same context menu as Library tab build item except possibility to rename branch title:

#### Rename Branch

:   Rename branch title (++return++ to submit new title, ++esc++ to reject editing).

### Custom Page

??? image "Screenshots"

    <figure>
      <img src="../imgs/user_custom.png"/>
      <figcaption>User Tab, Custom Page</figcaption>
    </figure>

Custom page contains builds that placed under [`custom`](library_folder.md#custom) directory of [`library folder`](library_folder.md). It acts the same way as the Library tab build item. After adding new builds inside the `custom` folder make sure to press the `Reload` button in the top left corner to force Blender Launcher to read it from the disk and show in the list.
