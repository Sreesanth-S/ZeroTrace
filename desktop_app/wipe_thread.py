from imports import *
from wipe_engine import WipeEngine

class WipeThread(QThread):
    """Thread for performing wipe operations"""
    progress_updated = pyqtSignal(int, str)
    wipe_completed = pyqtSignal(dict)  # Wipe result dict
    wipe_failed = pyqtSignal(str)

    def __init__(self, device_info, method, confirm):
        super().__init__()
        self.device_info = device_info
        self.method = method
        self.confirm = confirm
        self.wipe_engine = WipeEngine()
        self._stop_requested = False

    def run(self):
        try:
            def progress_callback(progress, message):
                self.progress_updated.emit(progress, message)

            result = self.wipe_engine.start_wipe(
                self.device_info, self.method, progress_callback
            )

            self.wipe_completed.emit(result)

        except Exception as e:
            self.wipe_failed.emit(str(e))

    def stop(self):
        """Stop the wipe operation"""
        self.wipe_engine.stop_wipe()
