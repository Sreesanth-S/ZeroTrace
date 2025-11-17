from PyQt5.QtCore import QThread, pyqtSignal
from wipe_engine import WipeEngine

class WipeThread(QThread):
    progress_updated = pyqtSignal(int, str)
    wipe_completed = pyqtSignal(dict) 
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

            # Start the wipe operation
            result = self.wipe_engine.start_wipe(
                self.device_info, 
                self.method, 
                progress_callback
            )

            # Check if wipe was successful
            if result.get('success') or result.get('status') in ['Completed', 'Cancelled']:
                self.wipe_completed.emit(result)
            else:
                error_msg = result.get('error', 'Unknown error occurred')
                self.wipe_failed.emit(error_msg)

        except Exception as e:
            self.wipe_failed.emit(str(e))

    def stop(self):
        self._stop_requested = True
        self.wipe_engine.stop_wipe()