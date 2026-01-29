from dataclasses import dataclass
from functools import cache

from PySide6.QtGui import QColor, QIcon, QPixmap

base_path = ":resources/icons/"

WHITE = QColor(255, 255, 255, 255)


@dataclass(frozen=True)
class Icons:
    settings: QIcon
    wiki: QIcon
    minimize: QIcon
    close: QIcon
    expand_more: QIcon
    expand_less: QIcon
    folder: QIcon
    favorite: QIcon
    fake: QIcon
    delete: QIcon
    filled_circle: QIcon
    quick_launch: QIcon
    download: QIcon
    update: QIcon
    file: QIcon
    taskbar: QIcon
    bl_file: QIcon
    none: QIcon

    @classmethod
    @cache
    def get(cls, color=WHITE):
        return cls(
            load_icon(color, "settings"),
            load_icon(color, "wiki"),
            load_icon(color, "minimize"),
            load_icon(color, "close"),
            load_icon(color, "expand_more"),
            load_icon(color, "expand_less"),
            load_icon(color, "folder"),
            load_icon(color, "favorite"),
            load_icon(color, "fake"),
            load_icon(color, "delete"),
            load_icon(color, "filled_circle"),
            load_icon(color, "quick_launch"),
            load_icon(color, "download"),
            load_icon(color, "update"),
            load_icon(color, "file"),
            QIcon(base_path + "bl/bl.ico"),
            QIcon(base_path + "bl/bl_file.ico"),
            QIcon(),
        )


def load_icon(color, name):
    pixmap = QPixmap(base_path + name + "")
    image = pixmap.toImage()

    for y in range(image.height()):
        for x in range(image.height()):
            color.setAlpha(image.pixelColor(x, y).alpha())
            image.setPixelColor(x, y, color)

    pixmap = QPixmap.fromImage(image)
    return QIcon(pixmap)


def get_bl_file_location():
    import sys
    from pathlib import Path

    from modules.platform_utils import get_cwd, is_frozen

    assert sys.platform == "win32"
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", "")) / "files" / "bl_file.ico"

    return get_cwd() / "source" / "resources" / "icons" / "bl" / "bl_file.ico"
