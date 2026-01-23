# Implementing a New Blender Fork

This guide documents the steps to add support for a new Blender fork to the launcher.

## Overview

Adding a new fork requires changes across multiple layers:

1. **Scraping** - Fetch build information from fork's distribution source
2. **Settings** - Add configuration options for visibility and updates
3. **UI** - Create library and download pages
4. **Build Processing** - Handle fork-specific executable names, versioning, and structure
5. **Extraction** - Handle fork-specific archive formats and directory structures

## 1. Create Scraper

Create a new scraper in `source/threads/scraping/<fork_name>.py`:

### Basic Scraper Structure

```python
from modules.build_info import BuildInfo
from modules._platform import get_platform
from threads.scraping.base import BuildScraper
from modules.connection_manager import ConnectionManager

class Scraper<ForkName>(BuildScraper):
    def __init__(self, man: ConnectionManager):
        super().__init__()
        self.manager = man
    
    def scrape(self) -> Generator[BuildInfo, None, None]:
        # Fetch builds from fork's API/website
        # Yield BuildInfo objects for each build
        pass
```

### Key Implementation Details

**For GitHub Releases:**
```python
GITHUB_API_URL = "https://api.github.com/repos/<owner>/<repo>/releases"

def scrape(self):
    r = self.manager.request("GET", GITHUB_API_URL)
    releases = json.loads(r.data)
    
    for release in releases:
        for asset in release.get("assets", []):
            download_url = asset.get("browser_download_url")
            
            # Filter by platform
            if not self._matches_platform(asset["name"]):
                continue
            
            build_info = BuildInfo(
                download_url,
                str(version),
                commit_hash,
                commit_time,
                branch="fork-branch-name",
                custom_executable="fork-executable-name"
            )
            yield build_info
```

**Version Parsing:**
- Parse semantic versions from release tags or filenames
- Use `parse_blender_ver()` from `modules.build_info` for compatibility
- Map fork versions to Blender config versions if needed

## 2. Update Settings Module

Add settings functions in `source/modules/settings.py`:

### Visibility Settings

```python
# Show in Library tab
def get_show_fork_builds() -> bool:
    return get_settings().value("show_fork_builds", defaultValue=True, type=bool)

def set_show_fork_builds(b: bool):
    get_settings().setValue("show_fork_builds", b)

# Show in Downloads tab
def get_scrape_fork_builds() -> bool:
    return get_settings().value("scrape_fork_builds", defaultValue=True, type=bool)

def set_scrape_fork_builds(b: bool):
    get_settings().setValue("scrape_fork_builds", b)
```

### Update Button Settings

```python
def get_show_fork_update_button() -> bool:
    return get_settings().value("show_fork_update_button", defaultValue=True, type=bool)

def set_show_fork_update_button(is_checked):
    get_settings().setValue("show_fork_update_button", is_checked)

def get_fork_update_behavior() -> int:
    return get_settings().value("fork_update_behavior", defaultValue=2, type=int)

def set_fork_update_behavior(behavior):
    get_settings().setValue("fork_update_behavior", update_behavior[behavior])
```

### Update Settings Dictionaries

```python
library_pages = {
    # ... existing entries
    "<Fork Name>": 4,  # Next available index
}

downloads_pages = {
    # ... existing entries  
    "<Fork Name>": 4,  # Next available index
}

minimum_version_table = [
    # ... existing entries
    "<fork-branch>",
]
```

## 3. Add Update Manager Support

Update `source/modules/blender_update_manager.py`:

```python
def _branch_visibility(current_branch: str) -> bool:
    # ... existing checks
    fork_visibility = (
        get_show_fork_update_button() if get_use_advanced_update_button() 
        else get_show_update_button()
    )
    
    if current_branch == "<fork-branch>" and fork_visibility:
        return True
    # ...

def _get_update_behavior(current_branch: str) -> int:
    # ... existing checks
    fork_behavior = (
        get_fork_update_behavior() if get_use_advanced_update_button()
        else get_update_behavior()
    )
    
    if current_branch == "<fork-branch>":
        return fork_behavior
    # ...
```

## 4. Integrate Scraper

Update `source/threads/scraper.py`:

```python
from threads.scraping.fork import Scraperfork

class Scraper:
    def __init__(self, parent, man: ConnectionManager, build_cache=False):
        # ... existing code
        self.scrape_fork = get_scrape_fork_builds()
        self.scraper_fork = Scraperfork(self.manager)
    
    def scrapers(self):
        scrapers = []
        # ... existing scrapers
        if self.scrape_fork:
            scrapers.append(self.scraper_fork)
        return scrapers
    
    def get_download_links(self):
        # Add platform filter if needed
        if "fork" in build.link.lower():
            self.links.emit(build)
```

## 5. Update Library Drawer

Update `source/threads/library_drawer.py`:

```python
@dataclass
class DrawLibraryTask(Task):
    folders: Iterable[str | Path] = (
        "stable",
        "daily",
        "experimental",
        "bforartists",
        "<fork-branch>",  # Add fork folder
        "custom",
    )
```

**Add executable detection** in `get_blender_builds()`:
```python
has_fork_exe = (path / build / fork_exe).is_file()

yield (
    folder / build,
    has_blinfo or has_blender_exe or has_fork_exe,
)
```

## 6. Add UI Pages

Update `source/windows/main_window.py`:

### Create Page Widgets

```python
def draw(self, polish=False):
    # Library page
    self.LibraryforkPageWidget = BasePageWidget(
        parent=self,
        page_name="LibraryforkListWidget",
        time_label="Commit Time",
        info_text="Nothing to show yet",
        extended_selection=True,
    )
    self.LibraryforkListWidget = self.LibraryToolBox.add_page_widget(
        self.LibraryforkPageWidget, "<Fork Name>"
    )
    
    # Downloads page
    self.DownloadsforkPageWidget = BasePageWidget(
        parent=self,
        page_name="DownloadsforkListWidget",
        time_label="Upload Time",
        info_text="No new builds available",
    )
    self.DownloadsforkListWidget = self.DownloadsToolBox.add_page_widget(
        self.DownloadsforkPageWidget, "<Fork Name>"
    )
```

### Update Scraper Integration

```python
def start_scraper(self, scrape_fork=None, ...):
    if scrape_fork is None:
        scrape_fork = get_scrape_fork_builds()
    
    if scrape_fork:
        self.DownloadsforkPageWidget.set_info_label_text("Checking for new builds")
    else:
        self.DownloadsforkPageWidget.set_info_label_text("Checking disabled")
    
    self.DownloadsforkListWidget.clear_()
    self.scraper.scrape_fork = scrape_fork

def draw_to_downloads(self, build_info: BuildInfo):
    # ... existing branches
    elif branch == "<fork-branch>":
        downloads_list_widget = self.DownloadsforkListWidget
        library_list_widget = self.LibraryforkListWidget

def draw_to_library(self, path: Path, ...):
    # ... existing branches
    elif branch == "<fork-branch>":
        library = self.LibraryforkListWidget
```

### Update Visibility Controls

```python
def update_visible_lists(self, force_l_fork=False, force_s_fork=False, ...):
    show_fork = force_l_fork or get_show_fork_builds()
    scrape_fork = force_s_fork or get_scrape_fork_builds()
    
    self.LibraryToolBox.setTabVisible(X, show_fork)
    self.LibraryToolBox.setTabEnabled(X, show_fork)
    self.DownloadsToolBox.setTabVisible(X, scrape_fork)
    self.DownloadsToolBox.setTabEnabled(X, scrape_fork)
```

## 7. Update Settings UI

Update `source/widgets/settings_window/blender_builds_tab.py`:

```python
def __init__(self, parent: BlenderLauncher):
    # Connect signals
    self.repo_group.fork_repo.library_changed.connect(set_show_fork_builds)
    self.repo_group.fork_repo.download_changed.connect(set_scrape_fork_builds)
    
    # Add update button checkbox
    self.ShowforkUpdateButton = QCheckBox()
    self.ShowforkUpdateButton.setText("Show fork Update Button")
    self.ShowforkUpdateButton.clicked.connect(self.show_fork_update_button)
    self.ShowforkUpdateButton.setChecked(get_show_fork_update_button())
    
    # Add update behavior combo
    self.UpdateforkBehavior = QComboBox()
    self.UpdateforkBehavior.addItems(list(update_behavior.keys()))
    self.UpdateforkBehavior.setCurrentIndex(get_fork_update_behavior())
    self.UpdateforkBehavior.activated[int].connect(self.change_update_fork_behavior)
```

### Add Repository Widget

Update `source/widgets/repo_group.py`:

```python
def __init__(self, parent=None):
    self.fork_repo = RepoUserView(
        "<Fork Name>",
        "Fork description",
        library=get_show_fork_builds(),
        download=get_scrape_fork_builds(),
        parent=self,
    )
    
    self.repos = [
        # ... existing repos
        self.fork_repo,
    ]
```

## 8. Handle Download and Extraction

Update `source/widgets/download_widget.py`:

```python
def init_extractor(self, source: Path) -> None:
    # ... existing branches
    elif self.build_info.branch == "<fork-branch>":
        dist = library_folder / "<fork-branch>"
```

### Handle Fork-Specific Archive Structures

If fork uses non-standard archive structure, update `source/threads/extractor.py`:

```python
def _fix_fork_structure(build_path: Path) -> Path:
    """
    Fix fork-specific directory structure after extraction.
    
    Example: Move nested folders, flatten bin/Release structures, etc.
    """
    # Implement fork-specific structure fixes
    return build_path

# Call in ExtractTask.run():
result = _fix_fork_structure(result)
```

## 9. Handle Fork-Specific Versioning

If fork uses different versioning than Blender:

### Add Version Matcher

In `source/modules/build_info.py`:

```python
def fork_version_matcher(fork_version: Version) -> Version | None:
    """
    Map fork version to Blender config version.
    
    Example: UPBGE 0.40 -> Blender 4.0
             Bforartists 5.0 -> Blender 5.1
    """
    versions = read_blender_version_list()
    
    # Implement version mapping logic
    matching_version = Version(major, minor)
    
    if matching_version in versions:
        return matching_version
    return None
```

### Add to BuildInfo

```python
@property
def fork_version_matcher(self):
    return fork_version_matcher(self.semversion)
```

## 10. Handle Config Folders

Fork-specific config paths are centralized in `source/modules/build_info.py` using the `FORK_CONFIG_PATHS` dictionary.

### Add Fork Config to FORK_CONFIG_PATHS

In `source/modules/build_info.py`, add your fork's config paths:

```python
FORK_CONFIG_PATHS = {
    "bforartists": {
        "config_folder": "bforartists",
        "config_subfolder": "bforartists",
    },
    "upbge": {
        "config_folder": "UPBGE",
        "config_subfolder": {
            "Windows": "Blender",
            "Linux": "upbge",
            "macOS": "UPBGE",
        },
    },
    "<fork-branch>": {
        "config_folder": "<Fork Foundation>",     
        "config_subfolder": "<fork>",             
        # OR for platform-specific subfolders:
        # "config_subfolder": {
        #     "Windows": "<windows-subfolder>",
        #     "Linux": "<linux-subfolder>",
        #     "macOS": "<macos-subfolder>",
        # },
    },
}
```

**Notes:**

- `config_folder`: Used only on Windows (e.g., `%APPDATA%\<config_folder>\`)
- `config_subfolder`: 
    - **Simple string**: Same subfolder for all platforms (Linux: `~/.config/<subfolder>/`, macOS: `~/Library/Application Support/<subfolder>/`)
    - **Platform dict**: Different subfolder per platform (Windows uses it too: `%APPDATA%\<config_folder>\<subfolder>\`)

The `get_fork_config_paths(branch)` function retrieves these paths automatically.

### Portable Mode Support

Update `make_portable_path()` in `source/widgets/library_widget.py`:

```python
def make_portable_path(self) -> Path:
    branch = self.build_info.branch
    
    if branch == "<fork-branch>" and version >= "X.Y":
        folder_name = "portable"
        config_path = self.link / folder_name
    # ... existing logic
```

## 11. Finding Config Paths in Fork Source Code

When implementing support for a fork, you need to determine where the fork stores its configuration files. This information is defined in the fork's C++ source code in platform-specific system path files.

### Location of System Path Files

Config paths are defined in these three files in the fork's repository:

```
intern/ghost/intern/GHOST_SystemPathsUnix.cc      # Linux
intern/ghost/intern/GHOST_SystemPathsWin32.cc     # Windows
intern/ghost/intern/GHOST_SystemPathsCocoa.mm     # macOS
```

### What to Look For

In each file, look for the `getUserDir()` function. This function returns the config folder path.

#### Linux (GHOST_SystemPathsUnix.cc)

Look for `getUserDir()` function. The config path is typically set in one of these patterns:

```cpp
// Pattern 1: XDG_CONFIG_HOME environment variable
home = getenv("XDG_CONFIG_HOME");
if (home) {
    user_path = string(home) + "/blender/" + versionstr;  // <-- "blender" is the folder name
}

// Pattern 2: Fallback to ~/.config
else {
    home = home_dir_get();
    if (home) {
        user_path = string(home) + "/.config/blender/" + versionstr;  // <-- "blender" is the folder name
    }
}
```

**What to extract:** The folder name after `/` or `/.config/` (e.g., `"blender"`, `"upbge"`, `"bforartists"`)

#### Windows (GHOST_SystemPathsWin32.cc)

Look for `getUserDir()` function. The config path uses Windows roaming app data:

```cpp
HRESULT hResult = SHGetKnownFolderPath(
    FOLDERID_RoamingAppData, KF_FLAG_DEFAULT, nullptr, &knownpath_16);

if (hResult == S_OK) {
    conv_utf_16_to_8(knownpath_16, knownpath, MAX_PATH * 3);
    strcat(knownpath, "\\Blender Foundation\\Blender\\");  // <-- "Blender Foundation" and "Blender" are the folder names
    strcat(knownpath, versionstr);
    user_dir = knownpath;
}
```

**What to extract:** 
- The organization name (e.g., `"Blender Foundation"`, `"UPBGE Foundation"`)
- The application subfolder (e.g., `"Blender"`, `"upbge"`, `"Bforartists"`)

Full path example: `%APPDATA%\Blender Foundation\Blender\4.3\`

#### macOS (GHOST_SystemPathsCocoa.mm)

Look for `getUserDir()` function. It calls `GetApplicationSupportDir()`:

```cpp
static const char *GetApplicationSupportDir(const char *versionstr,
                                           const NSSearchPathDomainMask mask,
                                           char *tempPath,
                                           const std::size_t len_tempPath)
{
    @autoreleasepool {
        NSArray *paths = NSSearchPathForDirectoriesInDomains(NSApplicationSupportDirectory, mask, YES);
        NSString *basePath = [paths objectAtIndex:0];
        
        snprintf(tempPath,
                len_tempPath,
                "%s/Blender/%s",  // <-- "Blender" is the folder name
                [basePath cStringUsingEncoding:NSASCIIStringEncoding],
                versionstr);
    }
    return tempPath;
}
```

**What to extract:** The folder name in the snprintf format string (e.g., `"Blender"`, `"upbge"`, `"Bforartists"`)

Full path example: `~/Library/Application Support/Blender/4.3/`

### Real-World Examples

#### Official Blender
- **Linux**: `~/.config/blender/4.3/`
- **Windows**: `%APPDATA%\Blender Foundation\Blender\4.3\`
- **macOS**: `~/Library/Application Support/Blender/4.3/`

Files: [Unix](https://projects.blender.org/blender/blender/src/branch/main/intern/ghost/intern/GHOST_SystemPathsUnix.cc) | [Win32](https://projects.blender.org/blender/blender/src/branch/main/intern/ghost/intern/GHOST_SystemPathsWin32.cc) | [Cocoa](https://projects.blender.org/blender/blender/src/branch/main/intern/ghost/intern/GHOST_SystemPathsCocoa.mm)

#### UPBGE
- **Linux**: `~/.config/upbge/0.40/`
- **Windows**: `%APPDATA%\UPBGE\Blender\0.40\`
- **macOS**: `~/Library/Application Support/UPBGE/0.40/`

Files: [Unix](https://github.com/UPBGE/upbge/blob/42a7572bd98f4787c72f77ad6f4c6ee8820faf55/intern/ghost/intern/GHOST_SystemPathsUnix.cc) | [Win32](https://github.com/UPBGE/upbge/blob/42a7572bd98f4787c72f77ad6f4c6ee8820faf55/intern/ghost/intern/GHOST_SystemPathsWin32.cc) | [Cocoa](https://github.com/UPBGE/upbge/blob/42a7572bd98f4787c72f77ad6f4c6ee8820faf55/intern/ghost/intern/GHOST_SystemPathsCocoa.mm)

#### Bforartists
- **Linux**: `~/.config/bforartists/5.1/`
- **Windows**: `%APPDATA%\Bforartists\bforartists\5.1\`
- **macOS**: `~/Library/Application Support/bforartists/5.1/`

Files: [Unix](https://github.com/Bforartists/Bforartists/blob/master/intern/ghost/intern/GHOST_SystemPathsUnix.cc) | [Win32](https://github.com/Bforartists/Bforartists/blob/master/intern/ghost/intern/GHOST_SystemPathsWin32.cc) | [Cocoa](https://github.com/Bforartists/Bforartists/blob/master/intern/ghost/intern/GHOST_SystemPathsCocoa.mm)

### Using This Information in Implementation

Once you've determined the config paths from the fork's source code (see section 11), add them to `FORK_CONFIG_PATHS` in `source/modules/build_info.py`:

**Example 1 - Same subfolder on all platforms (Bforartists):**

```python
FORK_CONFIG_PATHS = {
    # ... existing entries
    "bforartists": {
        "config_folder": "bforartists",      # Windows: %APPDATA%\bforartists\
        "config_subfolder": "bforartists",   # All platforms use same subfolder
    },
}
```

Results in:
- **Windows**: `%APPDATA%\bforartists\bforartists\5.1\`
- **Linux**: `~/.config/bforartists/5.1/`
- **macOS**: `~/Library/Application Support/bforartists/5.1/`

**Example 2 - Platform-specific subfolders (UPBGE):**

```python
FORK_CONFIG_PATHS = {
    # ... existing entries
    "upbge": {
        "config_folder": "UPBGE",            # Windows: %APPDATA%\UPBGE\
        "config_subfolder": {
            "Windows": "Blender",            # Windows uses different subfolder
            "Linux": "upbge",                # Linux uses lowercase
            "macOS": "UPBGE",                # macOS uses uppercase
        },
    },
}
```

Results in:
- **Windows**: `%APPDATA%\UPBGE\Blender\0.40\`
- **Linux**: `~/.config/upbge/0.40/`
- **macOS**: `~/Library/Application Support/UPBGE/0.40/`


## Key Files Reference

| Component | File Path |
|-----------|-----------|
| Scraper | `source/threads/scraping/fork.py` |
| Settings | `source/modules/settings.py` |
| Update Manager | `source/modules/blender_update_manager.py` |
| Main Window | `source/windows/main_window.py` |
| Settings UI | `source/widgets/settings_window/blender_builds_tab.py` |
| Repository Group | `source/widgets/repo_group.py` |
| Library Drawer | `source/threads/library_drawer.py` |
| Build Info & Config Paths | `source/modules/build_info.py` |
| Extractor | `source/threads/extractor.py` |
| Download Widget | `source/widgets/download_widget.py` |
| Library Widget | `source/widgets/library_widget.py` |
