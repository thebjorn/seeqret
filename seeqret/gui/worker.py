"""Background execution helper for slow facade calls.

   Slack traffic (OAuth, polls, sends) must not block the GUI
   thread. ``call_async`` runs a callable on a QThread and delivers
   the result (or the exception) back on the GUI thread.
"""
from PySide6.QtCore import QObject, QThread, Signal


class _Worker(QObject):
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def run(self):
        try:
            self.done.emit(self.fn())
        except Exception as e:
            self.failed.emit(str(e))


def call_async(parent, fn, on_done, on_error):
    """Run ``fn()`` on a worker thread.

       *on_done(result)* / *on_error(message)* fire on the GUI
       thread. The thread object is parented to *parent* so it
       isn't garbage-collected mid-flight.
    """
    thread = QThread(parent)
    worker = _Worker(fn)
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.done.connect(on_done)
    worker.failed.connect(on_error)
    worker.done.connect(thread.quit)
    worker.failed.connect(thread.quit)
    thread.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)
    # keep a reference until the thread winds down
    thread._worker = worker
    thread.start()
    return thread
