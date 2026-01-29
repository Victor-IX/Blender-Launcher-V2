from __future__ import annotations

from pathlib import Path

# resources_rc needs to be imported after PySide6 because
# if there are any errors importing PySide6
# it would be registered as an issue fetching the resources instead
import PySide6  # noqa: F401
from modules.platform_utils import is_frozen

try:
    import resources_rc  # noqa: F401

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
