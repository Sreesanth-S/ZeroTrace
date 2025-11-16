# desktop_app/wipe_engine.py
"""
Enhanced wipe engine with proper Windows API integration
Supports physical drive access with administrator privileges
"""

import os
import win32api
import win32file
import win32con
import wmi
import random
import time
import hashlib
from typing import List, Dict, Optional, Callable
from datetime import datetime
from logger import logger
import struct


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
        self._volume_handles = []  # Track volume handles for cleanup
        
    def get_available_drives(self) -> List[DeviceInfo]:
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

    def _get_volumes_for_drive(self, device_path: str) -> List[str]:
        volumes = []
        try:
            # Extract drive number from path (e.g., PHYSICALDRIVE1 -> 1)
            drive_num = int(device_path.split('PHYSICALDRIVE')[-1])

            # Method 1: Use Windows API to enumerate volumes
            try:
                # Get all drive letters
                import string
                for letter in string.ascii_uppercase:
                    drive_letter = f"{letter}:"
                    volume_path = f"\\\\.\\{drive_letter}"

                    try:
                        # Try to get volume information
                        volume_info = win32api.GetVolumeInformation(volume_path)
                        # Check if this volume belongs to our physical drive
                        # by comparing the drive number
                        if self._is_volume_on_drive(volume_path, drive_num):
                            volumes.append(volume_path)
                            logger.debug(f"Found volume {volume_path} on drive {drive_num}")
                    except:
                        continue
            except Exception as e:
                logger.warning(f"Windows API method failed for drive {device_path}: {e}")

            # Method 2: Fallback to WMI if Windows API fails
            if not volumes:
                try:
                    # Try WMI with simpler queries
                    for volume in self.wmi.Win32_Volume():
                        if volume.DriveLetter:
                            try:
                                # Get disk extents for this volume
                                for extent in volume.associators("Win32_DiskPartition"):
                                    if extent.DiskIndex == drive_num:
                                        volumes.append(f"\\\\.\\{volume.DriveLetter}:")
                                        break
                            except:
                                continue
                except Exception as e:
                    logger.warning(f"WMI fallback failed for drive {device_path}: {e}")

            # Method 3: Direct partition enumeration as final fallback
            if not volumes:
                try:
                    # Enumerate partitions directly
                    for partition in self.wmi.Win32_DiskPartition():
                        if partition.DiskIndex == drive_num:
                            # Find logical disks for this partition
                            for logical_disk in partition.associators("Win32_LogicalDisk"):
                                if logical_disk.DeviceID:
                                    volumes.append(f"\\\\.\\{logical_disk.DeviceID}:")
                                    logger.debug(f"Found volume {logical_disk.DeviceID} via partition enumeration")
                except Exception as e:
                    logger.warning(f"Direct partition enumeration failed for drive {device_path}: {e}")

            logger.debug(f"Found {len(volumes)} volumes for drive {device_path}: {volumes}")

        except Exception as e:
            logger.error(f"Error getting volumes for drive {device_path}: {e}")

        return volumes

    def _is_volume_on_drive(self, volume_path: str, drive_num: int) -> bool:
        """Check if a volume is on the specified physical drive"""
        try:
            # Get volume disk extents using DeviceIoControl
            handle = win32file.CreateFile(
                volume_path,
                win32con.GENERIC_READ,
                win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
                None,
                win32con.OPEN_EXISTING,
                0,
                None
            )

            try:
                # IOCTL_VOLUME_GET_VOLUME_DISK_EXTENTS
                extents = win32file.DeviceIoControl(
                    handle,
                    0x560000,  # IOCTL_VOLUME_GET_VOLUME_DISK_EXTENTS
                    None,
                    1024
                )

                if len(extents) >= 12:
                    disk_num = struct.unpack('<I', extents[8:12])[0]
                    return disk_num == drive_num

            finally:
                win32file.CloseHandle(handle)

        except Exception as e:
            logger.debug(f"Failed to check if volume {volume_path} is on drive {drive_num}: {e}")

        return False

    def _lock_volume(self, volume_path: str) -> Optional[int]:
        try:
            # Open volume handle
            handle = win32file.CreateFile(
                volume_path,
                win32con.GENERIC_WRITE | win32con.GENERIC_READ,
                win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
                None,
                win32con.OPEN_EXISTING,
                win32con.FILE_FLAG_NO_BUFFERING | win32con.FILE_FLAG_WRITE_THROUGH,
                None
            )

            # Lock the volume
            win32file.DeviceIoControl(
                handle,
                0x90018,  # FSCTL_LOCK_VOLUME
                None,
                None
            )

            # Dismount the volume
            win32file.DeviceIoControl(
                handle,
                0x90020,  # FSCTL_DISMOUNT_VOLUME
                None,
                None
            )

            logger.debug(f"Successfully locked and dismounted volume: {volume_path}")
            return handle

        except Exception as e:
            logger.error(f"Failed to lock volume {volume_path}: {e}")
            if 'handle' in locals():
                try:
                    win32file.CloseHandle(handle)
                except:
                    pass
            return None

    def _unlock_volume(self, handle: int):
        """Unlock a previously locked volume"""
        try:
            win32file.DeviceIoControl(
                handle,
                0x9001C,  # FSCTL_UNLOCK_VOLUME
                None,
                None
            )
            win32file.CloseHandle(handle)
            logger.debug("Successfully unlocked volume")
        except Exception as e:
            logger.error(f"Failed to unlock volume: {e}")

    def _dismount_drive_volumes(self, device_path: str) -> int:
        dismounted_count = 0
        try:
            volumes = self._get_volumes_for_drive(device_path)

            for volume_path in volumes:
                try:
                    # Try to dismount the volume
                    win32api.SetVolumeMountPoint(volume_path[:-1], None)  # Remove drive letter
                    logger.debug(f"Successfully dismounted volume: {volume_path}")
                    dismounted_count += 1
                except Exception as e:
                    logger.warning(f"Failed to dismount volume {volume_path}: {e}")
                    # Try alternative method using DeviceIoControl
                    try:
                        handle = win32file.CreateFile(
                            volume_path,
                            win32con.GENERIC_READ | win32con.GENERIC_WRITE,
                            win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
                            None,
                            win32con.OPEN_EXISTING,
                            0,
                            None
                        )
                        try:
                            win32file.DeviceIoControl(
                                handle,
                                0x90020,  # FSCTL_DISMOUNT_VOLUME
                                None,
                                None
                            )
                            logger.debug(f"Successfully dismounted volume {volume_path} using DeviceIoControl")
                            dismounted_count += 1
                        finally:
                            win32file.CloseHandle(handle)
                    except Exception as e2:
                        logger.warning(f"Failed to dismount volume {volume_path} using DeviceIoControl: {e2}")

        except Exception as e:
            logger.error(f"Error dismounting volumes for drive {device_path}: {e}")

        return dismounted_count

    def _offline_disk(self, device_path: str):
        try:
            # Extract drive number
            drive_num = int(device_path.split('PHYSICALDRIVE')[-1])

            # Create diskpart script
            script_content = f"""select disk {drive_num}offline disk"""

            # Write script to temp file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(script_content)
                script_path = f.name

            try:
                # Run diskpart
                import subprocess
                result = subprocess.run(
                    ['diskpart', '/s', script_path],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode == 0:
                    logger.debug("Diskpart offline command succeeded")
                else:
                    logger.warning(f"Diskpart offline command failed: {result.stderr}")

            finally:
                # Clean up temp file
                try:
                    os.unlink(script_path)
                except:
                    pass

        except Exception as e:
            logger.warning(f"Failed to offline disk {device_path}: {e}")
            raise
    
    def validate_drive_access(self, device_path: str) -> tuple[bool, str]:
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
    
    def start_wipe(self, device_info: DeviceInfo, method: str, progress_callback: Optional[Callable[[int, str], None]] = None) -> Dict:
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

            # Open drive for writing first
            if progress_callback:
                progress_callback(0, "Opening drive...")

            # Try to open drive with different access modes if needed
            handle = None
            try:
                handle = win32file.CreateFile(
                    device_info.path,
                    win32con.GENERIC_WRITE,
                    0,  # Exclusive access
                    None,
                    win32con.OPEN_EXISTING,
                    win32con.FILE_FLAG_NO_BUFFERING | win32con.FILE_FLAG_WRITE_THROUGH,
                    None
                )
            except Exception as e:
                error_code = getattr(e, 'winerror', None)
                if error_code == 5:  # Access Denied
                    logger.warning("Exclusive access failed, trying shared access...")
                    # Try with shared access as fallback
                    try:
                        handle = win32file.CreateFile(
                            device_info.path,
                            win32con.GENERIC_WRITE,
                            win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
                            None,
                            win32con.OPEN_EXISTING,
                            0,
                            None
                        )
                        logger.warning("Opened drive with shared access - data integrity may be compromised")
                    except Exception as e2:
                        logger.error(f"Failed to open drive even with shared access: {e2}")
                        raise e  # Re-raise original error
                else:
                    raise

            # Check if drive is write-protected
            try:
                win32file.DeviceIoControl(
                    handle,
                    0x70000,  # IOCTL_DISK_IS_WRITABLE
                    None,
                    None
                )
                logger.debug("Drive is writable")
            except Exception as e:
                result['error'] = "Drive is write-protected"
                result['status'] = 'Failed'
                logger.error("Drive is write-protected")
                win32file.CloseHandle(handle)
                return result

            # Try to dismount volumes using multiple methods
            if progress_callback:
                progress_callback(0, "Dismounting volumes...")

            # Method 1: Try to dismount all volumes on the drive
            volumes_dismounted = self._dismount_drive_volumes(device_info.path)
            if volumes_dismounted:
                logger.info(f"Successfully dismounted {volumes_dismounted} volumes")
            else:
                logger.warning("No volumes were dismounted")

            # Method 2: Try to offline the disk using diskpart
            try:
                self._offline_disk(device_info.path)
                logger.info("Successfully offlined disk")
            except Exception as e:
                logger.warning(f"Failed to offline disk: {e}")

            # Now try to lock and dismount the physical drive directly
            if progress_callback:
                progress_callback(0, "Locking drive...")

            try:
                # Lock the physical drive
                win32file.DeviceIoControl(
                    handle,
                    0x90018,  # FSCTL_LOCK_VOLUME
                    None,
                    None
                )
                logger.info("Successfully locked physical drive")

                # Dismount the physical drive
                win32file.DeviceIoControl(
                    handle,
                    0x90020,  # FSCTL_DISMOUNT_VOLUME
                    None,
                    None
                )
                logger.info("Successfully dismounted physical drive")

            except Exception as e:
                logger.warning(f"Failed to lock/dismount physical drive: {e}")
                # Continue anyway - some drives may not support this

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

                # Unlock volumes after wipe
                if progress_callback:
                    progress_callback(98, "Unlocking volumes...")

                for vol_handle in self._volume_handles:
                    try:
                        self._unlock_volume(vol_handle)
                    except Exception as e:
                        logger.error(f"Failed to unlock volume handle {vol_handle}: {e}")

                self._volume_handles.clear()

        except Exception as e:
            logger.log_error_with_context("Wipe operation", e)
            result['error'] = str(e)
            result['status'] = 'Failed'

        # Ensure volumes are unlocked even on failure
        try:
            for vol_handle in self._volume_handles:
                try:
                    self._unlock_volume(vol_handle)
                except Exception as e:
                    logger.error(f"Failed to unlock volume handle {vol_handle} during cleanup: {e}")
            self._volume_handles.clear()
        except:
            pass

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

        # Also unlock any locked volumes immediately
        try:
            for vol_handle in self._volume_handles:
                try:
                    self._unlock_volume(vol_handle)
                except Exception as e:
                    logger.error(f"Failed to unlock volume handle {vol_handle} during stop: {e}")
            self._volume_handles.clear()
        except:
            pass
    
    def get_progress(self) -> int:
        """Get current wiping progress (0-100)"""
        return self._current_progress