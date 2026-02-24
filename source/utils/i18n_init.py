import locale
import logging
import os
import sys
from enum import StrEnum
from pathlib import Path

import i18n

logger = logging.getLogger(__name__)

if getattr(sys, "frozen", False):
    LOCALIZATION_PATH = Path(getattr(sys, "_MEIPASS", "")) / "localization/"
else:
    LOCALIZATION_PATH = Path("source/resources/localization").resolve()

i18n.load_path.append(LOCALIZATION_PATH)


class Language(StrEnum):
    AUTO = "auto"
    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    JAPANESE = "ja"

    @property
    def display_name(self) -> str:
        names = {
            Language.AUTO: "Auto",
            Language.ENGLISH: "English",
            Language.SPANISH: "Español",
            Language.FRENCH: "Français",
            Language.JAPANESE: "日本語",
        }
        return names[self]


def _detect_os_locale() -> str:
    """Detect the language code from the OS locale settings."""
    if sys.platform == "win32":
        import ctypes

        windll = ctypes.windll.kernel32
        try:
            loc = locale.windows_locale[windll.GetUserDefaultUILanguage()]
        except (KeyError, OSError):
            loc = "en_US"
    elif (x := os.environ.get("LANG")) is not None:
        loc = x
    elif (x := locale.getlocale()[0]) is not None:
        loc = x
    else:
        loc = "en_US"

    return loc.split("_", 1)[0]


def _get_saved_language() -> str | None:
    """Read the language setting directly from QSettings."""
    try:
        from modules.settings import get_language

        lang = get_language()
        if lang and lang != Language.AUTO:
            return lang
    except Exception:
        logger.debug("Could not read language setting, using auto-detection")
    return None


# Determine locale: saved preference takes priority over OS detection
loc = _get_saved_language() or _detect_os_locale()

i18n.set("plural_few", 1)
i18n.set("enable_memoization", True)
i18n.set("locale", loc)
i18n.set("fallback", "en")
i18n.set("skip_locale_root_data", True)
