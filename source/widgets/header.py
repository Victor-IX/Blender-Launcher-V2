from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

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

        # Left side: action buttons packed together
        for widget in widgets:
            layout.addWidget(widget, 0)

        # Center: title label with stretch
        self.label = QLabel(label, self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label, 1)

        # Right side: window controls
        self.minimize_button = None
        if use_minimize:
            self.minimize_button = WHeaderButton(parent.icons.minimize, "")
            self.minimize_button.setProperty("HeaderButton", True)
            self.minimize_button.clicked.connect(self.minimize_signal.emit)
            layout.addWidget(self.minimize_button, 0)

        self.close_button = WHeaderButton(parent.icons.close, "")
        self.close_button.setProperty("HeaderButton", True)
        self.close_button.setProperty("CloseButton", True)
        self.close_button.clicked.connect(self.close_signal.emit)
        layout.addWidget(self.close_button, 0)
