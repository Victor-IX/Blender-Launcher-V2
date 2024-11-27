from PyQt5.QtWidgets import QMessageBox
from typing import List, Tuple, Optional


class PopupWidget(QMessageBox):
    def __init__(
        self,
        title: str,
        message: str,
        info_popup: Optional[bool] = False,
        buttons: Optional[List[Tuple[str, QMessageBox.StandardButton]]] = None,
        parent=None,
    ):
        """
        Popup class.

        :param title:   The title of the popup.
        :param message: The message to display in the popup.
        :param buttons: Optional. A list of tuples with the button label and the button role.
                        If not provided, the popup will have an OK and a Cancel button.
        :param info_popup: Optional. If True, the popup will be an information popup with only a Ok button.
        :param parent: The parent widget. Optional.
        """
        super().__init__(parent)

        self.title = title
        self.message = message
        self.info_popup = info_popup
        self.buttons = buttons

        self.setWindowTitle(title)
        self.setText(message)

        if self.buttons:
            for label, role in buttons:
                self.addButton(label, role)
        elif self.info_popup:
            self.addButton(self.Ok)
            self.exec()
        else:
            self.addButton(self.Ok)
            self.addButton(self.Cancel)

    def exec_popup(self):
        # Return True False For Simple Popups to make it easier to use
        if not self.buttons:
            if self.exec() == self.Ok:
                return True
            else:
                return False
        return self.exec()
