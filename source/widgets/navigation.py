from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QButtonGroup, QLabel
from PySide6.QtCore import Signal, QSize, Qt

class SidebarWidget(QWidget):
    index_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 8, 0, 8)
        self.layout.setSpacing(8)
        
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)
        self.button_group.idClicked.connect(self.index_changed)

        self.setFixedWidth(64)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("SidebarWidget { background-color: #181818; }")

    def add_tab(self, icon, text, index):
        btn = QPushButton()
        btn.setIcon(icon)
        btn.setToolTip(text)
        btn.setCheckable(True)
        btn.setIconSize(QSize(28, 28))
        btn.setFixedSize(48, 48)
        
        # Simple styling for sidebar buttons
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 8px;
                margin: 0px 8px;
            }
            QPushButton:hover {
                background-color: #333333;
            }
            QPushButton:checked {
                background-color: #444444;
                border-left: 3px solid #F5792A;
            }
        """)
        
        self.layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.button_group.addButton(btn, index)
        
        if index == 0:
            btn.setChecked(True)
            
    def add_spacer(self):
        self.layout.addStretch(1)

    def add_action_button(self, icon, text):
        """Add a standalone button not part of the tab group (e.g., settings)."""
        btn = QPushButton()
        btn.setIcon(icon)
        btn.setToolTip(text)
        btn.setIconSize(QSize(28, 28))
        btn.setFixedSize(48, 48)

        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 8px;
                margin: 0px 8px;
            }
            QPushButton:hover {
                background-color: #333333;
            }
        """)

        self.layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        return btn

    def set_current_index(self, index):
        btn = self.button_group.button(index)
        if btn:
            btn.setChecked(True)
