# Build Initialization

??? image "Screenshots"

    <figure>
      <img src="../imgs/library_custom_build_initialization.png"/>
      <figcaption>Custom Build Library</figcaption>
    </figure>

Build initialization is used to set all the Blender Build information on the first installation of a [Custom Build](library_folder.md#custom).

## Initialization Options 

??? image "Screenshots"

    <figure>
      <img src="../imgs/library_custom_build_initialization_settings.png"/>
      <figcaption>Initialization Options</figcaption>
    </figure>

**Executable Name**: Enter the name of the executable for the custom Blender version[^exe].

**Auto Detect Information button**: If the executable file has been found, this option will be available. You can click on it to autofill all the build info fields.

**Subversion**: Which Blender version you are initializing.
:   Example format: 4.0.2
:   This may change appearance depending on which repo/branch you are initializing if they use a custom versioning scheme.

**Build Hash**: Unique commit ID. used to differentiate builds of the same "version" but were made at different points in time with different code.

**Commit Time**: Time when the build was created.

**Branch Name**: Name of the branch used to make the build[^branch].

**Custom Name**: Name the build will have in the Blender Launcher.

**Favorite**: If the build is favorited, it has a special tab in the launcher.

[^exe]:
    This supports auto-completion and will show you the existing available executable files as you type.

[^branch]:
    Note that branches don't always refer to which repo you are using. For instance, all `patch` builds, when installed, have a unique branch related to what pull request it was used for.
