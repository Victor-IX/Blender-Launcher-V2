from __future__ import annotations

import textwrap
from enum import Enum, StrEnum
from typing import Required, TypedDict, Unpack

from i18n import t
from modules.string_utils import patch_note_cleaner
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from windows.base_window import BaseWindow


class PopupType(StrEnum):
    Success = "msg.success"
    Info = "msg.info"
    Setup = "msg.setup"
    Warning = "msg.warning"
    Error = "msg.error"


class PopupIcon(Enum):
    WARNING = 1
    INFO = 2
    NONE = 3


class PopupButton(StrEnum):
    OK = "act.ok"
    ACCEPT = "act.accept"
    CANCEL = "act.cancel"
    QUIT = "act.quit"
    NEXT = "act.next"
    PREV = "act.prev"
    CONT = "act.cont"
    FINISH = "act.finish"
    YES = "act.yes"
    NO = "act.no"
    RETRY = "act.retry"
    UPDATE = "act.update"
    LATER = "act.later"

    RESTART_NOW = "act.restart_now"
    TRASH = "act.trash"
    REMOVE = "act.remove"
    DELETE = "act.delete"
    DONT_SHOW_AGAIN = "act.dont_show_again"
    MIGRATE = "act.migrate"
    OVERWRITE = "act.overwrite"
    GENERAL_FOLDER = "act.general_folder"
    KEEP_BOTH_VERSIONS = "act.keep_both_versions"
    MOVE_TO_NEW = "act.move_to_new"
    REMOVE_SETTINGS = "act.remove_settings"

    @staticmethod
    def info() -> list[PopupButton]:
        return [PopupButton.OK]

    @staticmethod
    def default() -> list[PopupButton]:
        return [PopupButton.OK, PopupButton.CANCEL]

    @staticmethod
    def yn() -> list[PopupButton]:
        return [PopupButton.YES, PopupButton.NO]


class PopupWindow(BaseWindow):
    accepted = Signal()
    cancelled = Signal()
    custom_signal = Signal(PopupButton)

    def __init__(
        self,
        *,
        popup_type: PopupType,
        icon: PopupIcon,
        message: str,
        buttons: PopupButton | list[PopupButton] | None = None,
        parent=None,
        app=None,
    ):
        """
        Popup class.

        :param title:   The title of the popup (only visible when system title bar is enabled).
        :param message: The message to display in the popup.
        :param buttons: Optional. A list of tuples with the button label and the button role.
                        If not provided, the popup will have an OK and a Cancel button.
        :param info_popup: Optional. If True, the popup will be an information popup with only an OK button.
        :param icon: Optional. The icon to display in the popup. Can be `PopupIcon.INFO` for an info icon
                     or `PopupIcon.WARNING` for a warning icon. Defaults to `PopupIcon.INFO`.
        :param parent: The parent widget. Optional.
        """
        super().__init__(parent=parent, app=app)

        self.ptype = popup_type
        self.message = message

        if buttons is None:
            buttons = PopupButton.default()
        elif isinstance(buttons, PopupButton):
            buttons = [buttons]

        self.btns: list[PopupButton] = buttons

        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowTitle(t(self.ptype.value))
        self.setMinimumSize(200, 100)

        self.PopupWidget = QWidget(self)
        self.PopupLayout = QVBoxLayout(self.PopupWidget)
        self.PopupLayout.setContentsMargins(10, 10, 10, 10)
        self.setCentralWidget(self.PopupWidget)

        self.IconLabel = QLabel()
        self.IconLabel.setScaledContents(True)
        self.IconLabel.setFixedSize(24, 24)

        if icon == PopupIcon.WARNING:
            self.IconLabel.setPixmap(QPixmap(":resources/icons/exclamation.svg"))
        elif icon == PopupIcon.INFO:
            self.IconLabel.setPixmap(QPixmap(":resources/icons/info.svg"))
        else:
            self.IconLabel.hide()

        # Wrap the message text manually, using message_label.setWordWrap(True) don't work as expected for some reason
        wrapped_lines = []
        for line in message.splitlines():
            if not line.strip():
                wrapped_lines.append("")
            else:
                wrapped = textwrap.wrap(line, width=70)
                wrapped_lines.extend(wrapped)
        wrapped_message = "\n".join(wrapped_lines)

        message_label = QLabel(wrapped_message)

        self.TextLayout = QHBoxLayout()
        self.TextLayout.setContentsMargins(4, 4, 6, 0)
        self.TextLayout.addWidget(self.IconLabel)
        self.TextLayout.addSpacing(5)
        self.TextLayout.addWidget(message_label)

        self.PopupLayout.addLayout(self.TextLayout)

        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowMinimizeButtonHint & ~Qt.WindowType.WindowMaximizeButtonHint
        )
        self._add_buttons()
        self.show()
        self.setFixedSize(self.size())

    def _add_buttons(self):
        button_layout = QHBoxLayout()

        if len(self.btns) > 2:
            for key in self.btns:
                button = self._create_button(key, self._custom_signal)
                button_layout.addWidget(button)
        elif len(self.btns) == 2:
            ok_button = self._create_button(self.btns[0], self._accept)
            cancel_button = self._create_button(self.btns[1], self._cancel)
            button_layout.addWidget(ok_button)
            button_layout.addWidget(cancel_button)
        else:
            ok_button = self._create_button(self.btns[0], self._accept)
            button_layout.addWidget(ok_button)

        self.PopupLayout.addLayout(button_layout)

    def _create_button(self, btn: PopupButton, callback):
        button = QPushButton(t(btn.value))
        button.setProperty("Popup", True)
        button.clicked.connect(lambda _, lbl=btn: callback(lbl) if callback == self._custom_signal else callback())
        return button

    def _custom_signal(self, label: PopupButton):
        self.custom_signal.emit(label)
        self.close()

    def _accept(self):
        self.accepted.emit()
        self.close()

    def _cancel(self):
        self.cancelled.emit()
        self.close()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape and self.btns != PopupButton.info():
            self._cancel()
        if event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter}:
            self._accept()


class __GenericPWARGS(TypedDict, total=False):
    message: Required[str]
    buttons: PopupButton | list[PopupButton]
    parent: BaseWindow
    app: QApplication


class UpdateNotificationWindow(BaseWindow):
    accepted = Signal()
    cancelled = Signal()

    def __init__(
        self,
        latest_tag: str,
        version_notes: list[tuple[str, str]] | None,
        parent=None,
    ):
        super().__init__(parent=parent)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowTitle(t("msg.info"))
        self.setMinimumWidth(380)

        self.PopupWidget = QWidget(self)
        self.PopupLayout = QVBoxLayout(self.PopupWidget)
        self.PopupLayout.setContentsMargins(10, 10, 10, 10)
        self.PopupLayout.setSpacing(8)
        self.setCentralWidget(self.PopupWidget)

        # Header row: icon + "New version X available!"
        icon_label = QLabel()
        icon_label.setScaledContents(True)
        icon_label.setFixedSize(24, 24)
        icon_label.setPixmap(QPixmap(":resources/icons/info.svg"))

        header_label = QLabel(t("msg.updates.new_version_available", version=latest_tag.lstrip("v")))

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(4, 4, 6, 0)
        header_layout.addWidget(icon_label)
        header_layout.addSpacing(5)
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        self.PopupLayout.addLayout(header_layout)

        # Scrollable per-version patch notes area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setMaximumHeight(300)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(4, 4, 4, 4)
        scroll_layout.setSpacing(6)

        if version_notes:
            for i, (tag, body) in enumerate(version_notes):
                if i > 0:
                    separator = QFrame()
                    separator.setFrameShape(QFrame.Shape.HLine)
                    separator.setFrameShadow(QFrame.Shadow.Sunken)
                    scroll_layout.addWidget(separator)

                section_widget = QWidget()
                section_layout = QVBoxLayout(section_widget)
                section_layout.setContentsMargins(2, 2, 2, 2)
                section_layout.setSpacing(4)

                version_label = QLabel(tag)
                version_label.setStyleSheet("font-weight: bold;")
                section_layout.addWidget(version_label)

                cleaned = patch_note_cleaner(body)
                notes_text = cleaned if cleaned else t("msg.updates.no_release_notes")
                notes_label = QLabel(notes_text)
                notes_label.setWordWrap(True)
                section_layout.addWidget(notes_label)

                scroll_layout.addWidget(section_widget)
        else:
            no_notes_label = QLabel(t("msg.updates.no_release_notes"))
            scroll_layout.addWidget(no_notes_label)

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        self.PopupLayout.addWidget(scroll_area)

        # Buttons
        button_layout = QHBoxLayout()
        update_btn = QPushButton(t(PopupButton.UPDATE.value))
        update_btn.setProperty("Popup", True)
        update_btn.clicked.connect(self._accept)
        later_btn = QPushButton(t(PopupButton.LATER.value))
        later_btn.setProperty("Popup", True)
        later_btn.clicked.connect(self._cancel)
        button_layout.addWidget(update_btn)
        button_layout.addWidget(later_btn)
        self.PopupLayout.addLayout(button_layout)

        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowMinimizeButtonHint & ~Qt.WindowType.WindowMaximizeButtonHint
        )
        self.show()
        self.setFixedWidth(self.width())

    def _accept(self):
        self.accepted.emit()
        self.close()

    def _cancel(self):
        self.cancelled.emit()
        self.close()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            self._cancel()
        if event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter}:
            self._accept()


class Popup:
    Type = PopupType
    Icon = PopupIcon
    Button = PopupButton
    Window = PopupWindow
    UpdateNotification = UpdateNotificationWindow

    @staticmethod
    def success(**kwargs: Unpack[__GenericPWARGS]) -> PopupWindow:
        return PopupWindow(popup_type=PopupType.Success, icon=PopupIcon.NONE, **kwargs)

    @staticmethod
    def info(**kwargs: Unpack[__GenericPWARGS]) -> PopupWindow:
        return PopupWindow(popup_type=PopupType.Info, icon=PopupIcon.INFO, **kwargs)

    @staticmethod
    def setup(**kwargs: Unpack[__GenericPWARGS]) -> PopupWindow:
        return PopupWindow(popup_type=PopupType.Setup, icon=PopupIcon.NONE, **kwargs)

    @staticmethod
    def warning(**kwargs: Unpack[__GenericPWARGS]) -> PopupWindow:
        return PopupWindow(popup_type=PopupType.Warning, icon=PopupIcon.WARNING, **kwargs)

    @staticmethod
    def error(**kwargs: Unpack[__GenericPWARGS]) -> PopupWindow:
        return PopupWindow(popup_type=PopupType.Error, icon=PopupIcon.WARNING, **kwargs)
