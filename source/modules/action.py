from abc import abstractmethod

from PyQt5.QtCore import QObject


class Action(QObject):
    def __post_init__(self):
        super().__init__()

    @abstractmethod
    def run(self):
        raise NotImplementedError