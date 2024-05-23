import logging
from subprocess import Popen

from modules._platform import SubprocessTracker
from PyQt5.QtCore import QThread, pyqtSignal

logger = logging.getLogger()


class Observer(QThread):
    count_changed = pyqtSignal(int)
    append_proc = pyqtSignal(Popen)

    def __init__(self, parent):
        QThread.__init__(self)
        self.parent = parent
        self.processes: list[Popen] = []
        self.append_proc.connect(self.handle_append_proc)

    def run(self):
        old_proc_count = len(self.processes)
        while self.parent:
            for proc in self.processes.copy():
                returncode = proc.poll()
                if returncode is not None:
                    proc.kill()
                    self.processes.remove(proc)

                    logging.debug(f"Process {proc} finished with exit code {returncode}")

                    if proc.stdout is not None and not proc.stdout.closed:
                        proc.stdout.close()
                    if proc.stderr is not None and not proc.stderr.closed:
                        proc.stderr.close()
                    continue

            proc_count = len(self.processes)
            if proc_count > 0:
                self.count_changed.emit(proc_count)
            else:
                return

            QThread.sleep(1)

    def handle_append_proc(self, proc):
        self.processes.append(proc)
        self.count_changed.emit(len(self.processes))
