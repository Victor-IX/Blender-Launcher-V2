# Development Setup

## Requirements

- Python >=3.10, <3.14 

!!! info "Note"
    
    All actions should be performed under repository root folder i.e. `./Blender-Launcher-V2`

!!! info "Project Manager"
    
    It's recommended to use [UV](https://docs.astral.sh/uv/getting-started/) as the project manager.


## Setting Up Development Environment

=== "pip"

    **Install virtualenv:**

    ```bash
    python -m pip install virtualenv
    ```

    **Create the virtual environment:**

    ```bash
    python -m virtualenv --clear --download .venv
    ```

    **Activate the virtual environment:**

    === "Windows (PowerShell)"

        ```ps1
        ./.venv/Scripts/activate.ps1
        ```

    === "Windows (CMD)"

        ```bat
        ./.venv/Scripts/activate
        ```

    === "Linux/macOS"

        ```bash
        source .venv/bin/activate
        ```

    **Minimum set of packages for building executable:**

    ```bash
    pip install -e .
    ```

    **All packages including development tools:**

    ```bash
    pip install -e ".[docs,ruff,pytest]"
    ```

=== "PDM"

    **Install dependencies:**

    ```bash
    pdm install
    ```

    **Install with all development groups:**

    ```bash
    pdm install --dev
    ```

    **Activate the virtual environment:**

    === "Windows (PowerShell)"

        ```ps1
        ./.venv/Scripts/activate.ps1
        ```

    === "Windows (CMD)"

        ```bat
        ./.venv/Scripts/activate
        ```

    === "Linux/macOS"

        ```bash
        source .venv/bin/activate
        ```

    Or run commands directly with PDM:

    ```bash
    pdm run python source/main.py
    ```

=== "UV"

    **Create the virtual environment:**

    ```bash
    uv venv
    ```

    **Install dependencies:**

    ```bash
    uv sync
    ```

    **Install with all extras:**

    ```bash
    uv sync --extra docs --extra ruff --extra pytest
    ```

    **Activate the virtual environment:**

    === "Windows (PowerShell)"

        ```ps1
        ./.venv/Scripts/activate.ps1
        ```

    === "Windows (CMD)"

        ```bat
        ./.venv/Scripts/activate
        ```

    === "Linux/macOS"

        ```bash
        source .venv/bin/activate
        ```

    Or run commands directly with UV:

    ```bash
    uv run source/main.py
    ```

## Running Blender Launcher

!!! info
    As of ([c90f33d](https://github.com/Victor-IX/Blender-Launcher-V2/commit/c90f33dfb710da509e50932bae3cbe5b588d8688)), cached Blender-Launcher-V2 files (such as resources_rc.py and global.qss) are no longer included in the source due to them artificially inflating git diffs. In order to generate them, run the `build_style.py` script located in the root project directory. Running Blender Launcher without these being built will result in an error.

### Build required resources

**Generate the cached resource files:**

```bash
python build_style.py
```

This creates necessary files like `resources_rc.py` and `global.qss` that are required to run the application.

### Run the application

=== "pip"

    ```bash
    python source/main.py
    ```

=== "PDM"

    ```bash
    pdm run bl
    ```

=== "UV"

    ```bash
    uv run source/main.py
    ```

## Building Blender Launcher Executable

!!! warning
    Executables made in PyInstaller must be built inside the target platform! You cannot build for a different platform other than your own.

### Build the executable

**Run the build script:**

=== "Windows"

    ```bat
    ./scripts/build_win.bat
    ```

=== "Linux"

    ```bash
    ./scripts/build_linux.sh
    ```

=== "macOS"

    ```bash
    ./scripts/build_mac.sh
    ```

This creates a standalone executable using PyInstaller.

**Locate the output:**

Look for bundled app under the `Blender-Launcher-V2/dist/release` folder.


## Documentation

### Preview the Documentation

**Start the local documentation server:**

=== "Windows"

    ```bat
    ./scripts/mkdocs_serve.bat
    ```

=== "Linux/macOS"

    ```bash
    ./scripts/mkdocs_serve.sh
    ```

Then open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in a web browser.

### Update the Documentation

!!! warning "Note"
    You should never edit the documentation in the gh-pages branch; this branch is used to publish the documentation.

**Edit documentation files:**

Make the desired modifications in the .md files under the `docs/mkdocs` directory.

### Publish the Documentation

!!! warning
    These scripts will only work if you have write access to the Blender-Launcher-V2 repo.

**Deploy to GitHub Pages:**

=== "Windows"

    ```bat
    ./scripts/mkdocs_publish.bat
    ```

=== "Linux/macOS"

    ```bash
    ./scripts/mkdocs_publish.sh
    ```

This builds and publishes the documentation to the gh-pages branch.

## Common Development Tasks

### Running Tests

=== "pip"

    ```bash
    pytest
    ```

=== "PDM"

    ```bash
    pdm run pytest
    ```

=== "UV"

    ```bash
    uv run pytest
    ```

### Code Formatting and Linting

**Check code with Ruff:**

```bash
ruff check .
```

**Format code with Ruff:**

```bash
ruff format .
```

### Updating Dependencies

=== "pip"

    ```bash
    pip install --upgrade -e ".[docs,ruff,pytest]"
    ```

=== "PDM"

    ```bash
    pdm update
    ```

=== "UV"

    ```bash
    uv sync --upgrade
    ```