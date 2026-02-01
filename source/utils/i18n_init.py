import sys
from pathlib import Path

import i18n

if getattr(sys, "frozen", False):
    LOCALIZATION_PATH = Path(getattr(sys, "_MEIPASS", "")) / "localization/"
else:
    LOCALIZATION_PATH = Path("source/localization").resolve()

i18n.load_path.append(LOCALIZATION_PATH)
i18n.set("fallback", "en")
