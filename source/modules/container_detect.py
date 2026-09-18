import os
from pathlib import Path

_DEBUG_IS_CONTAINED = "BLV2_CONTAINED" in os.environ

IS_FLATPAK = (
    bool(os.getenv("container"))  # noqa: SIM112 (flatpak 'container' env variable is lowercase -~-)
    or Path("/.flatpak-info").exists()
)


IS_CONTAINED = _DEBUG_IS_CONTAINED or IS_FLATPAK  # expand if necessary
