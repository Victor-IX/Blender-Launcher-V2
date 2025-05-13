<style>body {text-align: justify}</style>

# Development

## Requirements

- Linux or Windows x64
- Python >=3.10, <3.14


!!! info "Note"

    All actions should be performed under repository root folder i.e. `/Blender-Launcher-V2`!

### Preparing the virtual environment

1. Create the virtual environment

    ```bash
    python -m pip install virtualenv
    python -m virtualenv --clear --download .venv
    ```

    === "Windows (Powershell)"

        ```ps1
        .\.venv\Scripts\activate.ps1
        ```

    === "Windows (Cmd)"

        ```bat
        .\.venv\Scripts\activate
        ```

    ===+ "Linux"

        ```bash
        source .venv/bin/activate
        ```

2. Install dependencies

    === "Minimum set of packages for building executable"

        ```bash
        pip install -e .
        ```

    ===+ "All packages including development tools"

        ```bash
        pip install -e ".[docs,ruff,pytest]"
        ```

## Running Blender Launcher

!!! info

    As of ([c90f33d](https://github.com/Victor-IX/Blender-Launcher-V2/commit/c90f33dfb710da509e50932bae3cbe5b588d8688)), cached Blender-Launcher-V2 files (such as resources_rc.py and global.qss) are no longer included in the source due to them artificially inflating git diffs. In order to generate them, run the `build_style.py` script located in the root project directory. running Blender Launcher without these being built will result in an error.

```bash
python source/main.py
```

## Building Blender Launcher.exe

!!! warning

    Executables made in Pyinstaller must be built inside the target platform! You cannot build for a different platform other than your own.

=== "Windows"

    1. Run batch file

        ```
        .\scripts\build_win.bat
        ```

    2. Look for bundled app under the `Blender-Launcher-V2\dist\release` folder

=== "Linux"

    1. Run shell script file

        ```
        sh scripts/build_linux.sh
        ```

    2. Look for bundled app under the `Blender-Launcher-V2/dist/release` folder

## Documentation

### Preview the Documentation

=== "Windows"

    1. Run the batch file

        ```bat
        .\scripts\mkdocs_serve.bat
        ```

    2. [Open the Documentation](http://127.0.0.1:8000/) in a web browser.

=== "Linux"

    1. Run the shell script file

        ```sh
        sh ./scripts/mkdocs_serve.sh
        ```

    2. [Open the Documentation](http://127.0.0.1:8000/) in a web browser.

### Update the Documentation

!!! warning "Note"
    You should never edit the documentation in the gh-pages branch; this branch is used to publish the documentation.

Make the desired modifications in the .md files.

### Publish the Documentation

!!! warning

    These scripts will only work if you have write access to the Blender-Launcher-V2 repo.

Run the script

=== "Windows"

    ```bat 
    .\scripts\mkdocs_publish.bat
    ```

=== "Linux"

    ```bash
    sh ./script/mkdocs_publish.sh
    ```
