import os
import win32api
import win32file
import win32con
import random
import time
import logging
from datetime import datetime
from device_detector import get_removable_drives

class WipePattern:
    """Different patterns for secure wiping"""
    ZEROS = 0  # All zeros
    ONES = 1   # All ones
    RANDOM = 2 # Random data

class WipeEngine:
    """Engine for secure drive wiping operations"""
    
    def __init__(self):
        self._stop_requested = False
        self._current_progress = 0
        self._sector_size = 512  # Default sector size
        self._buffer_size = 1024 * 1024  # 1MB buffer for writing
        
    def get_available_drives(self):
        """Get list of available removable drives"""
        return get_removable_drives()
    
    def start_wipe(self, drive_path, progress_callback=None):
        """Start the secure wiping process"""
        self._stop_requested = False
        self._current_progress = 0

        try:
            # Open drive handle
            drive_handle = win32file.CreateFile(
                f"\\\\.\\{drive_path}",
                win32con.GENERIC_WRITE,
                win32con.FILE_SHARE_WRITE,
                None,
                win32con.OPEN_EXISTING,
                0,
                None
            )

            # Get drive geometry
            drive_size = win32file.GetFileSize(drive_handle)

            # Multiple pass secure wipe
            self._wipe_pass(drive_handle, drive_size, WipePattern.ONES, progress_callback, "Pass 1/4: Writing ones...")      # First pass: all ones
            self._wipe_pass(drive_handle, drive_size, WipePattern.ZEROS, progress_callback, "Pass 2/4: Writing zeros...")     # Second pass: all zeros
            self._wipe_pass(drive_handle, drive_size, WipePattern.RANDOM, progress_callback, "Pass 3/4: Writing random data...")    # Third pass: random data
            self._wipe_pass(drive_handle, drive_size, WipePattern.ZEROS, progress_callback, "Pass 4/4: Final zeros...")     # Final pass: all zeros

            # Close drive handle
            win32file.CloseHandle(drive_handle)

            return True

        except Exception as e:
            print(f"Error during wipe: {str(e)}")
            return False
    
    def _wipe_pass(self, drive_handle, drive_size, pattern, progress_callback=None, status_message=""):
        """Perform a single wipe pass with the specified pattern"""
        if self._stop_requested:
            return

        # Create buffer based on pattern
        if pattern == WipePattern.ZEROS:
            buffer = bytearray(self._buffer_size)
        elif pattern == WipePattern.ONES:
            buffer = bytearray([0xFF] * self._buffer_size)
        else:  # Random
            buffer = bytearray(random.getrandbits(8) for _ in range(self._buffer_size))

        bytes_written = 0
        win32file.SetFilePointer(drive_handle, 0, win32con.FILE_BEGIN)

        while bytes_written < drive_size and not self._stop_requested:
            # Calculate remaining bytes
            bytes_to_write = min(self._buffer_size, drive_size - bytes_written)

            if bytes_to_write < self._buffer_size:
                write_buffer = buffer[:bytes_to_write]
            else:
                write_buffer = buffer

            # Write to drive
            error_code, _ = win32file.WriteFile(drive_handle, write_buffer)
            if error_code != 0:
                raise Exception(f"Write failed with error code: {error_code}")

            bytes_written += bytes_to_write

            # Update progress (0-100)
            self._current_progress = int((bytes_written / drive_size) * 100)

            # Call progress callback if provided
            if progress_callback:
                progress_callback(self._current_progress, status_message)

            # Small delay to prevent system overload
            time.sleep(0.001)
    
    def stop_wipe(self):
        """Stop the wiping process"""
        self._stop_requested = True
    
    def get_progress(self):
        """Get current wiping progress (0-100)"""
        return self._current_progress

    def perform_wipe(self, device, method, confirm, progress_callback):
        """Perform wipe operation and return log file path"""
        if not confirm:
            raise Exception("Wipe operation not confirmed")

        # Create logs directory if it doesn't exist
        logs_dir = os.path.join(os.getcwd(), 'desktop_app', 'logs')
        os.makedirs(logs_dir, exist_ok=True)

        # Generate log file name with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"wipe_log_{device.replace(':', '')}_{timestamp}.txt"
        log_path = os.path.join(logs_dir, log_filename)

        # Set up logging
        logging.basicConfig(
            filename=log_path,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

        logger = logging.getLogger(__name__)

        try:
            logger.info(f"Starting wipe operation on device: {device}")
            logger.info(f"Wipe method: {method}")
            logger.info(f"Confirmed: {confirm}")

            # Perform the wipe
            success = self.start_wipe(device, progress_callback)

            if success:
                logger.info("Wipe operation completed successfully")
                return log_path
            else:
                logger.error("Wipe operation failed")
                raise Exception("Wipe operation failed")

        except Exception as e:
            logger.error(f"Wipe operation error: {str(e)}")
            raise
