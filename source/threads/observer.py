from subprocess import Popen

from PySide6.QtCore import QObject, QTimer, Signal, Slot

OBSERVER_INTERVAL = 1_000  # msec


class Observer(QObject):
    count_changed = Signal(int)
    started = Signal()
    finished = Signal()

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.processes: list[Popen] = []

        self.timer = QTimer(self)
        self.timer.setInterval(OBSERVER_INTERVAL)
        self.timer.setSingleShot(False)
        self.timer.timeout.connect(self.tick)

    def tick(self):
        finished = [(i, proc) for i, proc in enumerate(self.processes) if proc.poll() is not None]
        for idx, proc in finished[::-1]:
            proc.kill()
            self.processes.pop(idx)

        if finished:
            proc_count = len(self.processes)
            if proc_count == 0:
                self.timer.stop()
                self.finished.emit()

            self.count_changed.emit(proc_count)

    @Slot(Popen)
    def watch(self, proc: Popen):
        if not self.processes:
            self.timer.start()
            self.started.emit()

        self.processes.append(proc)
        self.count_changed.emit(len(self.processes))
