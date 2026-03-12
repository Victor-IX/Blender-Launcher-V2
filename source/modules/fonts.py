from dataclasses import dataclass

from PySide6.QtGui import QFont, QFontDatabase

_font_path = ":resources/fonts/OpenSans-SemiBold.ttf"


@dataclass(frozen=True)
class Fonts:
    font_10: QFont
    font_8: QFont

    @classmethod
    def get(cls) -> "Fonts":
        global _fonts
        if _fonts is None:
            QFontDatabase.addApplicationFont(_font_path)
            font_10 = QFont("Open Sans SemiBold", 10)
            font_10.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            font_8 = QFont("Open Sans SemiBold", 8)
            font_8.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            _fonts = cls(font_10, font_8)

        return _fonts


_fonts: Fonts | None = None
