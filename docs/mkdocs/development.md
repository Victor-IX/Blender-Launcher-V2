<style>body {text-align: justify}</style>

# Development

## Requirements

- Linux or Windows x64
- Python 3.9
- pdm

!!! warning

    To use different Python version, run `pdm use` to select the correct python interpreter

## Using Pdm

!!! info "Note"

    All actions should be performed under repository root folder i.e. `/Blender-Launcher-V2`!

### Preparing virtual environment

1. Install pdm package

        pip install pdm

2. Create the virtual environment

    ```bash
    python -m pip install virtualenv
    python -m virtualenv --clear --download .venv
    python -m ensurepip
    python -m pip install --upgrade pdm
    # Enter the virtual Environment
    pdm venv activate
    # ^ Execute the command this returns with!
    ```

3. Install dependencies

    === "Minimum set of packages for building executable"

        ```
        pip install -e .
        ```

    === "All set of packages including development tools"

        ```
        pdm install
        ```

## Running Blender Launcher

!!! info

    As of ([c90f33d](https://github.com/Victor-IX/Blender-Launcher-V2/commit/c90f33dfb710da509e50932bae3cbe5b588d8688)), cached Blender-Launcher-V2 files (such as resources_rc.py and global.qss) are no longer included in the source due to them artificially inflating git diffs. In order to generate them, run the `build_style.py` script located in the root project directory. running Blender Launcher without these being built will result in an error.

```bash
python source/main.py
```

## Building Blender Launcher .exe

!!! warning

    Executables made in Pyinstaller must be built inside the target platform! You cannot build for a different platform other than your own.

=== "Windows"

    1. Run batch file

        ```
        .\build_win.bat
        ```

    2. Look for bundled app under `Blender-Launcher-V2\dist\release` folder

=== "Linux"

    1. Run shell script file

        ```
        sh build_linux.sh
        ```

    2. Look for bundled app under `Blender-Launcher-V2/dist/release` folder


## Documentation

### Preview the Documentation

=== "Windows"
   1. Run the batch file
        ```
        .\script\mkdocs_serve.bat
        ```
   2. [Open the Documentation](http://127.0.0.1:8000/) in a web browser.

=== "Linux"
    1. Run the shell script file
        ```
        sh .\script\mkdocs_serve.sh
        ```
    2. [Open the Documentation](http://127.0.0.1:8000/) in a web browser.

### Update the Documentation

!!! warning "Note"
    You should never edit the documentation in the gh-pages branch; this branch is used to publish the documentation.

Make the desired modifications in the .md files.

### Publish the Documentation

=== "Windows"
   1. Run the batch file
        ```
        .\script\mkdocs_publish.bat
        ```

=== "Linux"
    1. Run the shell script file
        ```
        sh .\script\mkdocs_publish.sh
        ```