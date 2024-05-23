<style>body {text-align: justify}</style>
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

### Executable Name

Enter the name of the executable for the custom Blender version.
    
!!! info
    This supports auto-completion and will show you the existing available executable files as you type.

!!! warning
    Make sure to input the correct executable name and do not select the BlenderLauncher.exe file. 

### Auto Detect Information

If the executable file has been found, the Auto Detect Option will be available. You can click on it to autofill all the build info fields.

### Subversion

Subversion corresponds to the Blender version you are initializing.
Example format: 4.0.2

### Build Hash

Unique build ID.

### Commit Time

Time when the build was created. 

### Branch Name

Name of the branch used to make the build.

### Custom Name

Name the build will have in the Blender Launcher.

!!! info
    You can set any desired name here.

### Favorite

Add the build to the Favorite builds in the Blender Launcher.