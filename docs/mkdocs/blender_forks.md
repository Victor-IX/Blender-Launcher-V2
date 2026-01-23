# Blender Forks

Blender Launcher V2 supports multiple Blender forks in addition to official Blender builds. This page provides detailed information about each supported fork.

## Overview

The launcher supports the following Blender forks:

- **Bforartists** - A fork focused on improving the user interface and user experience
- **UPBGE** (Uchronia Project Blender Game Engine) - A fork dedicated to game development

## Bforartists

### What is Bforartists?

[Bforartists](https://www.bforartists.de/) is a fork of Blender that focuses on providing a more user-friendly interface and improved usability. It maintains compatibility with Blender while offering an alternative UI design philosophy.

### Version Information

- Bforartists uses its own version numbering that is offset by one minor version compared to Blender
- Example: Bforartists 5.0.0 is based on Blender 5.1.0
- Configuration files follow Blender's versioning scheme for compatibility

### Getting Bforartists Builds

The launcher automatically fetches Bforartists builds from their official Nextcloud server at `cloud.bforartists.de`.

To enable/disable Bforartists in the launcher:

1. Open **Settings** (gear icon)
2. Go to **Blender Builds** tab
3. Toggle **Bforartists** in the repository list
4. Enable/disable both **Library** (show installed builds) and **Download** (fetch new builds)

### Executable Names

Bforartists uses different executable names than Blender:

- **Windows**: `bforartists.exe`
- **Linux**: `bforartists`
- **macOS**: `Bforartists.app`


### Official Resources

- **Website**: <https://www.bforartists.de/>
- **Downloads**: <https://www.bforartists.de/download/>
- **Documentation**: <https://www.bforartists.de/wiki/>

## UPBGE (Uchronia Project Blender Game Engine)

### What is UPBGE?

[UPBGE](https://upbge.org/) is a fork of Blender that continues development of the Blender Game Engine (BGE), which was removed from official Blender in version 2.8. It's designed specifically for real-time game development and interactive 3D applications.

### Build Types

UPBGE offers two types of builds in the launcher:

#### UPBGE Stable

- **Branch**: `upbge-stable`
- **Description**: Stable releases for production use
- **Version Pattern**: Official numbered releases (e.g., 0.30, 0.36, 0.40)

#### UPBGE Weekly

- **Branch**: `upbge-weekly`
- **Description**: Alpha/development builds with latest features
- **Version Pattern**: Weekly alpha releases (e.g., 0.40-alpha)
- **Update Frequency**: Weekly updates

### Version Information

- UPBGE versions use a unique versioning scheme (e.g., 0.30, 0.36, 0.40)
- Configuration files are mapped to the underlying Blender version
- Example: UPBGE 0.40 uses Blender 4.0 configuration and is based on the same Blender version
- Minimum supported version in the launcher: 0.30

### Getting UPBGE Builds

UPBGE builds are fetched from the official GitHub repository at `github.com/UPBGE/upbge/releases`.

!!! info "GitHub Token for UPBGE"
    UPBGE builds are fetched from GitHub's API. If you frequently check for updates, consider adding a [GitHub Token](github_token.md) to avoid rate limiting (60 requests/hour without authentication, 5,000 with authentication).

To enable/disable UPBGE in the launcher:

1. Open **Settings** (gear icon)
2. Go to **Blender Builds** tab
3. Toggle **UPBGE** and/or **UPBGE Weekly** in the repository list
4. Enable/disable both **Library** and **Download** options for each type

### Executable Names

UPBGE uses the same executable names as Blender:

- **Windows**: `blender.exe`
- **Linux**: `blender`
- **macOS**: `Blender.app`

The launcher automatically identifies UPBGE builds by their directory structure and version information.

### Official Resources

- **Website**: <https://upbge.org/>
- **GitHub**: <https://github.com/UPBGE/upbge>
- **Documentation**: <https://upbge.org/docs/latest/>
- **Discord**: <https://discord.gg/8PcrtTJW2R>
- **Forum**: <https://blenderartists.org/c/game-engine/10>

## Configuration and Settings

### Library Folder Structure

Each fork has its own folder in the library:

```
Library Folder/
├── stable/          # Official Blender stable releases
├── daily/           # Official Blender daily builds
├── experimental/    # Official Blender experimental branches
├── bforartists/     # Bforartists builds
├── upbge-stable/    # UPBGE stable releases
├── upbge-weekly/    # UPBGE weekly/alpha builds
└── custom/          # Manual custom builds
```

See [Library Folder Structure](library_folder.md#structure) for more details.

### Visibility Settings

Control which forks appear in the launcher:

- **Library Tab**: Toggle to show/hide installed builds in the Library
- **Downloads Tab**: Toggle to check for and display available downloads

These settings are independent, allowing you to:

- Show installed builds without checking for new ones
- Check for new builds without displaying old ones
- Enable/disable individual fork types (e.g., UPBGE Stable but not UPBGE Weekly)

### Update Management

Each fork type has independent update settings when using **Advanced Update Button** mode:

1. **Show Update Button**: Display quick update button per fork
2. **Update Behavior**: Choose replacement or keep-both strategy
3. **Version Checking**: Automatic version comparison for update notifications

Configure these in **Settings → Blender Builds**.


### Custom Builds

If you want to use other Blender forks not officially supported, you can add them manually through the **User → Custom** library. See [Manual Build Installation](manual_build_installation.md) for details.
