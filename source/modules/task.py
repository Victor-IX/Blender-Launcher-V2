from abc import abstractmethod

from modules.enums import MessageType
from PySide6.QtCore import QObject, Signal


class Task(QObject):
    message = Signal(str, MessageType)

    def __post_init__(self):
        super().__init__()

    @abstractmethod
    def run(self):
        raise NotImplementedError
