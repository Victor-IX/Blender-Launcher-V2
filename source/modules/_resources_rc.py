from __future__ import annotations

import sys
from pathlib import Path

from modules._platform import is_frozen

try:
    import resources_rc
    # Upon importing resources_rc, the :resources QIODevice should be open,
    # and the contained styles should be available for use.
except ImportError:
    if is_frozen():
        print("Failed to import cached resources! Blender-Launcher-V2 was built without resources.")
    elif (Path.cwd() / "build_style.py").exists():
        # TODO: Attempt to build the style and check if it fails
        print("Resources were not built! Run python build_style.py to build the style.")
    else:
        raise

    sys.exit()
