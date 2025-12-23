from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

if TYPE_CHECKING:
    from collections.abc import Iterable

    from windows.base_window import BaseWindow


class WHeaderButton(QPushButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setIconSize(QSize(20, 20))
        self.setFixedSize(36, 32)


class WindowHeader(QWidget):
    minimize_signal = Signal()
    close_signal = Signal()

    def __init__(
        self,
        parent: BaseWindow,
        label: str = "",
        widgets: Iterable[QWidget] = (),
        use_minimize: bool = True,
    ):
        super().__init__(parent)
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.layout_ = layout
        self.setLayout(layout)

        buttons = list(widgets)
        self.label = QLabel(label, self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        buttons.append(self.label)

        self.close_button = WHeaderButton(parent.icons.close, "")
        self.close_button.setProperty("HeaderButton", True)
        self.close_button.setProperty("CloseButton", True)
        self.close_button.clicked.connect(self.close_signal.emit)

        self.minimize_button = None
        if use_minimize:
            self.minimize_button = WHeaderButton(parent.icons.minimize, "")
            self.minimize_button.setProperty("HeaderButton", True)
            self.minimize_button.clicked.connect(self.minimize_signal.emit)
            buttons.append(self.minimize_button)
        buttons.append(self.close_button)

        for widget in buttons:
            if widget is self.label:
                layout.addWidget(widget, 2)
            layout.addWidget(widget, 0)

        # make sure the label is centered despite the buttons surrounding the label
        # layout.setContentsMargins(max(int(margins * 36), 0), 0, 0, 0)
