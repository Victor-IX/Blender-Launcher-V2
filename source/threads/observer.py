from subprocess import Popen

from PySide6.QtCore import QThread, Signal


class Observer(QThread):
    count_changed = Signal(int)
    append_proc = Signal(Popen)

    def __init__(self, parent):
        QThread.__init__(self)
        self.parent = parent
        self.processes = []
        self.append_proc.connect(self.handle_append_proc)

    def run(self):
        while self.parent:
            for proc in self.processes:
                if proc.poll() is not None:
                    proc.kill()
                    self.processes.remove(proc)
                    proc_count = len(self.processes)

                    if proc_count > 0:
                        self.count_changed.emit(proc_count)
                    else:
                        return

            QThread.sleep(1)

        return

    def handle_append_proc(self, proc):
        self.processes.append(proc)
        self.count_changed.emit(len(self.processes))
