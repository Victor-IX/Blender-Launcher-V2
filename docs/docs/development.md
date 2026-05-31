# Development Setup

All actions mentioned in this page should be performed under the repository root folder i.e. `./Blender-Launcher-V2`.

## Requirements

- Python >=3.11, <3.15
- [UV](https://docs.astral.sh/uv/getting-started/) (optional)

It's entirely optional to use `uv` as the project manager, but is strongly recommended as we use its tooling such as its lockfile and dependency resolution. Every shell snippet in this doc after the "Setting Up" step will use uv run as a prefix to indicate it needs to be run in the virtual environment.


## Setting Up Development Environment

=== "pip"

    ```bash
    # Install virtualenv:
    python -m pip install virtualenv
    # Create the virtual environment
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

    **Install dependencies:**

    ```bash
    # Minimum set of packages for building the executable:
    pip install -e .
    # All packages including development tools
    pip install -e ".[docs,ruff,pytest]"
    ```

=== "PDM"

    ```bash
    # Create the virtual environment & install dependencies:
    pdm install
    # Install with all development groups:
    pdm install -G:all
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

=== "UV (recommended)"

    ```bash
    # Create the virtual environment & install dependencies
    uv sync --frozen
    # install with all extras (docs, ruff, pytest)
    uv sync --all-extras
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

## Running Blender Launcher[^resources]

```bash
# Generate the cached resource files:
# This creates necessary files like `resources_rc.py` and `global.qss`.
# This only needs to run once, unless you're updating widget styles.
uv run build_style.py

# Run the application
uv run source/main.py
```

## Building Blender Launcher Executable[^build-notes]

### Build the executable

**Run the build script:**

=== "Windows"

    ```bat
    uv run ./scripts/build_win.bat
    ```

=== "Linux"

    ```bash
    uv run sh ./scripts/build_linux.sh
    ```

=== "macOS"

    ```bash
    uv run sh ./scripts/build_mac.sh
    ```

These scripts will create a standalone executable using PyInstaller. Once finished, the executable can be found under the `Blender-Launcher-V2/dist/release` folder.


## Documentation

### Previewing the Documentation

```bash
cd docs
# prefix with `uv run` if not in the virtual env
uv run mkdocs serve --livereload
```
or use the provided `scripts/mkdocs_serve` scripts.

Then open the given link (likely [http://127.0.0.1:8000/](http://127.0.0.1:8000/)) in a web browser.

### Edit Documentation Files[^update-gh-pages]

Make the desired modifications in the .md files under the `docs/mkdocs` directory.

### Publish the Documentation [Collaborator Only][^collab-only]

```bat
cd docs
uv run mkdocs gh-deploy
```

or use the provided `scripts/mkdocs_publish` scripts.

This builds and publishes the documentation to the gh-pages branch.

## Common Development Tasks

### Running Tests

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

[^resources]:
    As of ([c90f33d](https://github.com/Victor-IX/Blender-Launcher-V2/commit/c90f33dfb710da509e50932bae3cbe5b588d8688) ~v2.4.0), cached Blender-Launcher-V2 files (such as resources_rc.py and global.qss) are no longer included in the source due to them artificially inflating git diffs. 
    
    In order to generate them, run the `build_style.py` script located in the root project directory. Running Blender Launcher without these being built will result in an error.

[^build-notes]:
    !!! warning "Cross-platform compilation"
        Executables made in PyInstaller must be built inside the target platform. **You cannot build for a different platform other than your own.**

[^update-gh-pages]:  
    **You should never edit the documentation in the gh-pages branch;** this branch is used to publish the documentation and is overwritten every time `mkdocs gh-deploy` is run.

[^collab-only]:
    These scripts will only work if you have write access to the Blender-Launcher-V2 repo.
