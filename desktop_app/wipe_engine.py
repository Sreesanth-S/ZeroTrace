import os
import win32api
import win32file
import win32con
import random
import time
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
    
    def start_wipe(self, drive_path):
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
            self._wipe_pass(drive_handle, drive_size, WipePattern.ONES)      # First pass: all ones
            self._wipe_pass(drive_handle, drive_size, WipePattern.ZEROS)     # Second pass: all zeros
            self._wipe_pass(drive_handle, drive_size, WipePattern.RANDOM)    # Third pass: random data
            self._wipe_pass(drive_handle, drive_size, WipePattern.ZEROS)     # Final pass: all zeros
            
            # Close drive handle
            win32file.CloseHandle(drive_handle)
            
            return True
            
        except Exception as e:
            print(f"Error during wipe: {str(e)}")
            return False
    
    def _wipe_pass(self, drive_handle, drive_size, pattern):
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
            
            # Small delay to prevent system overload
            time.sleep(0.001)
    
    def stop_wipe(self):
        """Stop the wiping process"""
        self._stop_requested = True
    
    def get_progress(self):
        """Get current wiping progress (0-100)"""
        return self._current_progress
