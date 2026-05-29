import os
from pathlib import Path

IS_FLATPAK = (
    bool(os.getenv("container"))  # noqa: SIM112 (flatpak 'container' env variable is lowercase -~-)
    or Path("/.flatpak-info").exists()
)

IS_CONTAINED = IS_FLATPAK # expand if necessary
