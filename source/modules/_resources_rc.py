from __future__ import annotations

# ruff: disable[F401]
import sys
import traceback
from pathlib import Path

# resources_rc needs to be imported after PySide6 because
# if there are any errors importing PySide6
# it would be registered as an issue fetching the resources instead
try:
    import PySide6
    import PySide6.QtCore
except ImportError as e:
    traceback.print_exc()
    print("Failed to import PySide6.")
    if "GLIBC" in e.msg:
        # try to fetch the current glibc version
        import subprocess

        try:
            current_glibc = subprocess.check_output(["ldd", "--version"], timeout=0.5)
            print(
                f"Your GLIBC version ({current_glibc.splitlines()[0].strip()}) may be older than this build's supported version."
            )
        except subprocess.TimeoutExpired:
            print("Your GLIBC version may be older than this build's supported version.")
        print("If you are attempting to run the Linux_x64 build, see if the Ubuntu builds work for you.")
        print(
            "Those are built on an older version of GLIBC and should be more compatible with more LTS and stable Linux versions."
        )

    sys.exit()


from modules.platform_utils import is_frozen

try:
    import resources_rc

    # Upon importing resources_rc, the :resources QIODevice should be open,
    # and the contained styles should be available for use.
    RESOURCES_AVAILABLE = True
except ImportError:
    RESOURCES_AVAILABLE = False
    if is_frozen():
        print("Failed to import cached resources! Blender-Launcher-V2 was built without resources.")
    elif (Path.cwd() / "build_style.py").exists():
        # TODO: Attempt to build the style and check if it fails
        print("Resources were not built! Run python build_style.py to build the style.")

    else:
        print("Resources were not built! build the style so the launcher looks right.")

        raise

# ruff: enable[F401]
