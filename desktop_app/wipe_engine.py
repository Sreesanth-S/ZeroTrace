# desktop_app/wipe_engine_enhanced.py
"""
Enhanced wipe engine with proper Windows API integration
Supports physical drive access with administrator privileges
"""

import os
import win32api
import win32file
import win32con
import wmi
import psutil
import random
import time
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Callable
from datetime import datetime
from logger import logger


class WipeMethod:
    """Wipe methods enumeration"""
    QUICK = "Quick Wipe"
    DOD_3_PASS = "DoD 3-Pass"
    DOD_7_PASS = "DoD 7-Pass"
    GUTMANN_35_PASS = "Gutmann 35-Pass"


class WipePattern:
    """Patterns for secure wiping"""
    ZEROS = 0
    ONES = 1
    RANDOM = 2


class DeviceInfo:
    """Device information structure"""
    def __init__(self, path: str, name: str, size: int, serial: str = "", model: str = ""):
        self.path = path
        self.name = name
        self.size = size
        self.serial = serial
        self.model = model
        self.size_gb = size / (1024 ** 3) if size > 0 else 0


class WipeEngine:
    """Enhanced drive wiping engine with Windows API support"""
    
    def __init__(self):
        self._stop_requested = False
        self._current_progress = 0
        self._sector_size = 512
        self._buffer_size = 1024 * 1024  # 1MB buffer
        self.wmi = wmi.WMI()
        
    def get_available_drives(self) -> List[DeviceInfo]:
        """
        Get list of available removable physical drives with detailed information
        Filters out system/internal drives for safety

        Returns:
            List of DeviceInfo objects for removable drives only
        """
        drives = []

        try:
            # Get physical drives using WMI
            for physical_disk in self.wmi.Win32_DiskDrive():
                try:
                    # Skip system/internal drives for safety
                    media_type = getattr(physical_disk, 'MediaType', '').lower()
                    interface_type = getattr(physical_disk, 'InterfaceType', '').lower()
                    device_id = physical_disk.DeviceID or ""

                    # Check if this is a removable/external drive
                    is_removable = (
                        'removable' in media_type or
                        'external' in media_type or
                        interface_type == 'usb' or
                        'usb' in (physical_disk.Caption or '').lower() or
                        'usb' in (physical_disk.Model or '').lower()
                    )

                    # Skip system drives (usually PHYSICALDRIVE0 and internal SSDs)
                    is_system_drive = (
                        device_id.endswith('PHYSICALDRIVE0') or
                        'ssd' in (physical_disk.Caption or '').lower() or
                        'ssd' in (physical_disk.Model or '').lower() or
                        'nvme' in (physical_disk.Caption or '').lower() or
                        'nvme' in (physical_disk.Model or '').lower()
                    )

                    # Only include removable drives, exclude system drives
                    if is_removable and not is_system_drive:
                        device_info = DeviceInfo(
                            path=device_id,  # e.g., \\.\PHYSICALDRIVE1
                            name=physical_disk.Caption or physical_disk.Model or "Removable Drive",
                            size=int(physical_disk.Size) if physical_disk.Size else 0,
                            serial=physical_disk.SerialNumber or "",
                            model=physical_disk.Model or ""
                        )

                        drives.append(device_info)
                        logger.debug(f"Found removable drive: {device_info.name} ({device_info.size_gb:.2f} GB) - {media_type}")
                    else:
                        logger.debug(f"Skipped drive: {physical_disk.Caption} - MediaType: {media_type}, Interface: {interface_type}, System: {is_system_drive}")

                except Exception as e:
                    logger.error(f"Error getting drive info: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error enumerating drives: {e}")

        return drives
    
    def get_drive_by_path(self, path: str) -> Optional[DeviceInfo]:
        """Get specific drive information by path"""
        drives = self.get_available_drives()
        for drive in drives:
            if drive.path == path:
                return drive
        return None
    
    def validate_drive_access(self, device_path: str) -> tuple[bool, str]:
        """
        Validate that we can access the drive
        
        Args:
    device_path: Physical drive path (e.g., \\\\.\\PHYSICALDRIVE0)
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Try to open the device for reading
            handle = win32file.CreateFile(
                device_path,
                win32con.GENERIC_READ,
                win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
                None,
                win32con.OPEN_EXISTING,
                0,
                None
            )
            win32file.CloseHandle(handle)
            return True, "Drive accessible"
            
        except Exception as e:
            error_code = getattr(e, 'winerror', None)
            
            if error_code == 5:  # Access Denied
                return False, "Access Denied: Please run the application as Administrator"
            elif error_code == 2:  # File Not Found
                return False, "Drive not found: The device may have been disconnected"
            elif error_code == 32:  # Sharing Violation
                return False, "Drive is in use: Please close all applications using this drive"
            else:
                return False, f"Cannot access drive: {str(e)}"
    
    def start_wipe(self, device_info: DeviceInfo, method: str, 
                   progress_callback: Optional[Callable[[int, str], None]] = None) -> Dict:
        """
        Start secure wipe operation
        
        Args:
            device_info: Device information
            method: Wipe method to use
            progress_callback: Optional callback for progress updates (progress%, message)
            
        Returns:
            Dictionary with wipe results
        """
        self._stop_requested = False
        self._current_progress = 0
        
        start_time = datetime.now()
        
        result = {
            'success': False,
            'device_id': device_info.path,
            'device_name': device_info.name,
            'device_serial': device_info.serial,
            'device_model': device_info.model,
            'device_size': device_info.size,
            'method': method,
            'start_time': start_time.isoformat(),
            'end_time': None,
            'duration': None,
            'status': 'Started',
            'passes_completed': 0,
            'completion_hash': None,
            'error': None
        }
        
        try:
            logger.log_wipe_start(device_info.name, method)
            
            # Validate access first
            can_access, error_msg = self.validate_drive_access(device_info.path)
            if not can_access:
                result['error'] = error_msg
                result['status'] = 'Failed'
                logger.error(f"Drive validation failed: {error_msg}")
                return result
            
            # Open drive for writing
            if progress_callback:
                progress_callback(0, "Opening drive...")
            
            handle = win32file.CreateFile(
                device_info.path,
                win32con.GENERIC_WRITE,
                0,  # Exclusive access
                None,
                win32con.OPEN_EXISTING,
                0,
                None
            )
            
            try:
                # Determine number of passes based on method
                if method == WipeMethod.QUICK:
                    passes = [WipePattern.ZEROS]
                elif method == WipeMethod.DOD_3_PASS:
                    passes = [WipePattern.ZEROS, WipePattern.ONES, WipePattern.RANDOM]
                elif method == WipeMethod.DOD_7_PASS:
                    passes = [WipePattern.ZEROS, WipePattern.ONES, WipePattern.RANDOM,
                            WipePattern.ZEROS, WipePattern.ONES, WipePattern.RANDOM,
                            WipePattern.ZEROS]
                else:  # Gutmann
                    passes = [WipePattern.RANDOM] * 35
                
                total_passes = len(passes)
                
                # Perform wipe passes
                for pass_num, pattern in enumerate(passes, 1):
                    if self._stop_requested:
                        result['status'] = 'Cancelled'
                        break
                    
                    if progress_callback:
                        progress_callback(
                            int((pass_num - 1) / total_passes * 100),
                            f"Pass {pass_num}/{total_passes}: Writing {self._get_pattern_name(pattern)}"
                        )
                    
                    self._wipe_pass(handle, device_info.size, pattern, progress_callback)
                    result['passes_completed'] = pass_num
                
                # Generate completion hash
                if not self._stop_requested:
                    if progress_callback:
                        progress_callback(95, "Generating verification hash...")
                    
                    result['completion_hash'] = self._generate_completion_hash(device_info, method)
                    result['status'] = 'Completed'
                    result['success'] = True
                
            finally:
                win32file.CloseHandle(handle)
                
        except Exception as e:
            logger.log_error_with_context("Wipe operation", e)
            result['error'] = str(e)
            result['status'] = 'Failed'
        
        # Record end time and duration
        end_time = datetime.now()
        result['end_time'] = end_time.isoformat()
        duration = end_time - start_time
        result['duration'] = str(duration)
        
        logger.log_wipe_complete(device_info.name, result['status'], result['duration'])
        
        if progress_callback:
            progress_callback(100, f"Wipe {result['status']}")
        
        return result
    
    def _wipe_pass(self, handle, drive_size: int, pattern: int,
                   progress_callback: Optional[Callable[[int, str], None]] = None):
        """Perform a single wipe pass"""
        # Create buffer based on pattern
        if pattern == WipePattern.ZEROS:
            buffer = bytes(self._buffer_size)
        elif pattern == WipePattern.ONES:
            buffer = bytes([0xFF] * self._buffer_size)
        else:  # Random
            buffer = bytes(random.getrandbits(8) for _ in range(self._buffer_size))
        
        bytes_written = 0
        win32file.SetFilePointer(handle, 0, win32con.FILE_BEGIN)
        
        while bytes_written < drive_size and not self._stop_requested:
            # Calculate remaining bytes
            bytes_to_write = min(self._buffer_size, drive_size - bytes_written)
            
            if bytes_to_write < self._buffer_size:
                write_buffer = buffer[:bytes_to_write]
            else:
                write_buffer = buffer
            
            # Write to drive
            error_code, _ = win32file.WriteFile(handle, write_buffer)
            if error_code != 0:
                raise Exception(f"Write failed with error code: {error_code}")
            
            bytes_written += bytes_to_write
            self._current_progress = int((bytes_written / drive_size) * 100)
            
            # Log progress periodically
            if bytes_written % (self._buffer_size * 100) == 0:
                logger.log_wipe_progress(handle, self._current_progress)
            
            # Small delay to prevent system overload
            time.sleep(0.001)
    
    def _generate_completion_hash(self, device_info: DeviceInfo, method: str) -> str:
        """Generate SHA-256 hash for wipe verification"""
        hash_data = f"{device_info.path}:{device_info.serial}:{method}:{datetime.now().isoformat()}"
        return hashlib.sha256(hash_data.encode()).hexdigest()
    
    def _get_pattern_name(self, pattern: int) -> str:
        """Get human-readable pattern name"""
        if pattern == WipePattern.ZEROS:
            return "zeros"
        elif pattern == WipePattern.ONES:
            return "ones"
        else:
            return "random data"
    
    def stop_wipe(self):
        """Stop the wiping process"""
        logger.info("Wipe stop requested")
        self._stop_requested = True
    
    def get_progress(self) -> int:
        """Get current wiping progress (0-100)"""
        return self._current_progress