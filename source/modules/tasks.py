from __future__ import annotations

import logging
from collections import deque
from typing import TYPE_CHECKING, Any

from modules.enums import MessageType
from modules.task import Task
from PySide6.QtCore import QThread, Signal, Slot

if TYPE_CHECKING:
    from collections.abc import Callable


class TaskQueue(deque[Task]):
    message = Signal(str, MessageType)

    def __init__(
        self,
        worker_count=4,
        parent=None,
        maxlen=None,
        new_workers_on_crash=True,
        on_spawn: Callable[[TaskWorker], Any] | None = None,
    ):
        if maxlen:
            super().__init__(maxlen=maxlen)
        else:
            super().__init__()
        self.parent = parent
        self.workers: dict[TaskWorker, Task | None] = {}
        self.on_spawn: Callable[[TaskWorker], Any] | None = on_spawn
        for i in range(worker_count):
            self.spawn_new_worker(readd_on_crash=new_workers_on_crash, name=str(i))

    def spawn_new_worker(self, start=False, readd_on_crash=False, name: str | None = None):
        w = TaskWorker(queue=self, parent=self.parent)
        if self.on_spawn is not None:
            self.on_spawn(w)

        def update_listener_dct(item, w=w):
            self.workers[w] = item
            if item is not None:
                logging.debug(f"{w}: {item!r}")

        w.item_changed.connect(update_listener_dct)
        if readd_on_crash:

            def remake_worker():
                self.workers.pop(w)
                self.spawn_new_worker(start, readd_on_crash, name)

            w.finished.connect(remake_worker)

        if name is not None:
            w.setObjectName(name)
        self.workers[w] = None
        if start:
            w.start()

    def thread_with_task(self, task: Task):
        for listener, a in self.workers.items():
            if a == task:
                return listener
        return None

    def get_busy_threads(self):
        return {worker: item for worker, item in self.workers.items() if item is not None}

    def start(self):
        for worker in self.workers:
            worker.start()

    def fullstop(self):
        for worker, item in list(self.workers.items()):
            if worker.isRunning():
                worker.fullstop()
                if item is not None:
                    logging.debug(f"Stopped {worker} {item}")


class TaskWorker(QThread):
    item_changed = Signal(object)  # Task | None
    message = Signal(str, MessageType)
    error = Signal(Exception)

    def __init__(self, queue: TaskQueue, parent=None):
        super().__init__(parent)
        self.queue = queue
        self.item: Task | None = None

    def run(self):
        empty = False
        while True:
            try:
                self.item = self.queue.popleft()
            except IndexError:
                if empty:
                    QThread.msleep(500)
                else:
                    self.item_changed.emit(None)
                    empty = True
                continue

            empty = False
            self.item_changed.emit(self.item)

            self.item.message.connect(self.send_message)
            try:
                self.item.run()
            except Exception as e:
                logging.exception(e)
                self.error.emit(e)
            self.item.message.disconnect(self.send_message)

    @Slot(str, MessageType)
    def send_message(self, s, mtp):
        self.message.emit(s, mtp)

    @Slot()
    def fullstop(self):
        self.terminate()

    def __repr__(self):
        return f"{self.__class__.__name__}[{self.objectName()}]"
