import locale
import os
import sys
from pathlib import Path

import i18n

if getattr(sys, "frozen", False):
    LOCALIZATION_PATH = Path(getattr(sys, "_MEIPASS", "")) / "localization/"
else:
    LOCALIZATION_PATH = Path("source/localization").resolve()

i18n.load_path.append(LOCALIZATION_PATH)


# determine the language the user is using
loc: str
if sys.platform == "win32":
    import ctypes

    windll = ctypes.windll.kernel32
    loc = locale.windows_locale[windll.GetUserDefaultUILanguage()]
elif (x := os.environ.get("LANG")) is not None:
    loc = x
elif (x := locale.getlocale()[0]) is not None:
    loc = x
else:
    loc = "en_US"

loc = loc.split("_", 1)[0]

i18n.set("locale", loc)
i18n.set("fallback", "en")
