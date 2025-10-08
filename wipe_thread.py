from imports import *
from wipe_engine import WipeEngine

class WipeThread(QThread):
    """Thread for performing wipe operations"""
    progress_updated = pyqtSignal(int, str)
    wipe_completed = pyqtSignal(object)  # Path to log file
    wipe_failed = pyqtSignal(str)
    
    def __init__(self, device, method, confirm):
        super().__init__()
        self.device = device
        self.method = method
        self.confirm = confirm
        self.wipe_engine = WipeEngine()
    
    def run(self):
        try:
            def progress_callback(progress, message):
                self.progress_updated.emit(progress, message)
            
            log_path = self.wipe_engine.perform_wipe(
                self.device, self.method, self.confirm, progress_callback
            )
            
            if log_path:
                self.wipe_completed.emit(log_path)
            else:
                self.wipe_failed.emit("Failed to create wipe log")
                
        except Exception as e:
            self.wipe_failed.emit(str(e))