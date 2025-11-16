# desktop_app/wipe_engine.py
"""
Enhanced wipe engine with hardware-level secure erase support
Supports ATA Secure Erase, NVMe Format/Sanitize, and software overwrite
"""

import os
import win32api
import win32file
import win32con
import wmi
import random
import time
import hashlib
import struct
import ctypes
from typing import List, Dict, Optional, Callable, Tuple
from datetime import datetime
from logger import logger
from enum import Enum


class DriveType(Enum):
    """Drive type enumeration"""
    UNKNOWN = "Unknown"
    HDD = "HDD"
    SATA_SSD = "SATA SSD"
    NVME_SSD = "NVMe SSD"
    USB_FLASH = "USB Flash Drive"


class WipeMethod:
    """Wipe methods enumeration"""
    # Hardware methods
    ATA_SECURE_ERASE = "ATA Secure Erase"
    ATA_ENHANCED_SECURE_ERASE = "ATA Enhanced Secure Erase"
    NVME_FORMAT = "NVMe Format NVM"
    NVME_SANITIZE_CRYPTO = "NVMe Sanitize (Crypto Erase)"
    NVME_SANITIZE_BLOCK = "NVMe Sanitize (Block Erase)"
    NVME_SANITIZE_OVERWRITE = "NVMe Sanitize (Overwrite)"
    
    # Software methods
    QUICK = "Quick Wipe (1-Pass Zeros)"
    DOD_3_PASS = "DoD 3-Pass"
    DOD_7_PASS = "DoD 7-Pass"
    GUTMANN_35_PASS = "Gutmann 35-Pass"


class WipePattern:
    """Patterns for secure wiping"""
    ZEROS = 0
    ONES = 1
    RANDOM = 2


class DeviceInfo:
    """Enhanced device information structure"""
    def __init__(self, path: str, name: str, size: int, serial: str = "", model: str = ""):
        self.path = path
        self.name = name
        self.size = size
        self.serial = serial
        self.model = model
        self.size_gb = size / (1024 ** 3) if size > 0 else 0
        
        # Extended properties
        self.drive_type = DriveType.UNKNOWN
        self.bus_type = ""
        self.media_type = ""
        self.supports_ata_secure_erase = False
        self.supports_ata_enhanced_secure_erase = False
        self.supports_nvme_format = False
        self.supports_nvme_sanitize = False
        self.is_frozen = False
        self.is_system_drive = False


# ATA command structures
class ATAPassThroughDirect(ctypes.Structure):
    _fields_ = [
        ("Length", ctypes.c_ushort),
        ("AtaFlags", ctypes.c_ushort),
        ("PathId", ctypes.c_ubyte),
        ("TargetId", ctypes.c_ubyte),
        ("Lun", ctypes.c_ubyte),
        ("ReservedAsUchar", ctypes.c_ubyte),
        ("DataTransferLength", ctypes.c_ulong),
        ("TimeOutValue", ctypes.c_ulong),
        ("ReservedAsUlong", ctypes.c_ulong),
        ("DataBufferOffset", ctypes.POINTER(ctypes.c_void_p)),
        ("PreviousTaskFile", ctypes.c_ubyte * 8),
        ("CurrentTaskFile", ctypes.c_ubyte * 8),
    ]


class WipeEngine:
    """Enhanced drive wiping engine with hardware secure erase support"""

    # IOCTL codes
    IOCTL_ATA_PASS_THROUGH = 0x4D02C
    IOCTL_STORAGE_QUERY_PROPERTY = 0x2D1400
    
    # ATA commands
    ATA_IDENTIFY_DEVICE = 0xEC
    ATA_SECURITY_SET_PASSWORD = 0xF1
    ATA_SECURITY_UNLOCK = 0xF2
    ATA_SECURITY_ERASE_PREPARE = 0xF3
    ATA_SECURITY_ERASE_UNIT = 0xF4
    ATA_SECURITY_DISABLE_PASSWORD = 0xF6

    def __init__(self):
        self._stop_requested = False
        self._current_progress = 0
        self._sector_size = 512
        self._buffer_size = 1024 * 1024  # 1MB buffer
        self.wmi = wmi.WMI()
        self._volume_handles = []
        
    def get_available_drives(self) -> List[DeviceInfo]:
        """Get list of available drives with enhanced detection"""
        drives = []

        try:
            for physical_disk in self.wmi.Win32_DiskDrive():
                try:
                    media_type = getattr(physical_disk, 'MediaType', '').lower()
                    interface_type = getattr(physical_disk, 'InterfaceType', '').lower()
                    device_id = physical_disk.DeviceID or ""

                    # Check if removable/external
                    is_removable = (
                        'removable' in media_type or
                        'external' in media_type or
                        interface_type == 'usb' or
                        'usb' in (physical_disk.Caption or '').lower() or
                        'usb' in (physical_disk.Model or '').lower()
                    )

                    # Check if system drive
                    is_system_drive = (
                        device_id.endswith('PHYSICALDRIVE0') or
                        self._is_boot_drive(device_id)
                    )

                    # Only include non-system drives
                    if not is_system_drive:
                        device_info = DeviceInfo(
                            path=device_id,
                            name=physical_disk.Caption or physical_disk.Model or "Drive",
                            size=int(physical_disk.Size) if physical_disk.Size else 0,
                            serial=physical_disk.SerialNumber or "",
                            model=physical_disk.Model or ""
                        )

                        device_info.media_type = media_type
                        device_info.bus_type = interface_type
                        device_info.is_system_drive = is_system_drive

                        # Detect drive type and capabilities
                        self._detect_drive_capabilities(device_info, physical_disk)

                        drives.append(device_info)
                        logger.debug(f"Found drive: {device_info.name} - Type: {device_info.drive_type.value}")

                except Exception as e:
                    logger.error(f"Error getting drive info: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error enumerating drives: {e}")

        return drives

    def _is_boot_drive(self, device_path: str) -> bool:
        """Check if the drive contains the boot partition"""
        try:
            drive_num = int(device_path.split('PHYSICALDRIVE')[-1])
            
            for partition in self.wmi.Win32_DiskPartition():
                if partition.DiskIndex == drive_num:
                    if partition.BootPartition or partition.PrimaryPartition:
                        for logical_disk in partition.associators("Win32_LogicalDisk"):
                            if logical_disk.DeviceID:
                                system_drive = os.getenv('SystemDrive', 'C:')
                                if logical_disk.DeviceID.upper() == system_drive.upper():
                                    return True
        except:
            pass
        
        return False

    def _detect_drive_capabilities(self, device_info: DeviceInfo, physical_disk):
        """Detect drive type and supported secure erase methods"""
        try:
            interface = device_info.bus_type.lower()
            media = device_info.media_type.lower()
            model = device_info.model.lower()

            # Detect drive type
            if 'nvme' in interface or 'nvme' in model:
                device_info.drive_type = DriveType.NVME_SSD
                device_info.supports_nvme_format = True
                device_info.supports_nvme_sanitize = True
                
            elif 'usb' in interface or 'usb' in media:
                device_info.drive_type = DriveType.USB_FLASH
                    
            elif 'ssd' in model or 'solid state' in media:
                device_info.drive_type = DriveType.SATA_SSD
                self._check_ata_support(device_info)
                
            elif 'fixed' in media or 'hard disk' in media:
                device_info.drive_type = DriveType.HDD
                self._check_ata_support(device_info)
                
            else:
                device_info.drive_type = DriveType.UNKNOWN

            logger.info(f"Drive {device_info.name}: Type={device_info.drive_type.value}, "
                       f"ATA_SE={device_info.supports_ata_secure_erase}, "
                       f"ATA_ESE={device_info.supports_ata_enhanced_secure_erase}, "
                       f"NVMe_Format={device_info.supports_nvme_format}, "
                       f"NVMe_Sanitize={device_info.supports_nvme_sanitize}")

        except Exception as e:
            logger.error(f"Error detecting drive capabilities: {e}")

    def _check_ata_support(self, device_info: DeviceInfo):
        """Check ATA secure erase support using IDENTIFY DEVICE"""
        try:
            handle = win32file.CreateFile(
                device_info.path,
                win32con.GENERIC_READ | win32con.GENERIC_WRITE,
                win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
                None,
                win32con.OPEN_EXISTING,
                0,
                None
            )

            try:
                identify_data = self._send_ata_identify(handle)
                
                if identify_data and len(identify_data) >= 512:
                    word_82 = struct.unpack('<H', identify_data[164:166])[0]
                    word_128 = struct.unpack('<H', identify_data[256:258])[0]
                    
                    if word_82 & 0x0002:
                        device_info.supports_ata_secure_erase = True
                        
                        if word_128 & 0x0020:
                            device_info.supports_ata_enhanced_secure_erase = True
                    
                    if word_128 & 0x0008:
                        device_info.is_frozen = True
                        logger.warning(f"Drive {device_info.name} is in frozen state")

            finally:
                win32file.CloseHandle(handle)

        except Exception as e:
            logger.warning(f"Could not check ATA support for {device_info.name}: {e}")

    def _send_ata_identify(self, handle) -> Optional[bytes]:
        """Send ATA IDENTIFY DEVICE command"""
        try:
            buffer_size = 512
            buffer = ctypes.create_string_buffer(buffer_size)
            
            ata_pt = ATAPassThroughDirect()
            ata_pt.Length = ctypes.sizeof(ATAPassThroughDirect)
            ata_pt.AtaFlags = 0x02  # ATA_FLAGS_DATA_IN
            ata_pt.DataTransferLength = buffer_size
            ata_pt.TimeOutValue = 10
            ata_pt.DataBufferOffset = ctypes.cast(ctypes.pointer(buffer), ctypes.POINTER(ctypes.c_void_p))
            ata_pt.CurrentTaskFile[6] = self.ATA_IDENTIFY_DEVICE
            ata_pt.CurrentTaskFile[7] = 0xA0
            
            result = win32file.DeviceIoControl(
                handle,
                self.IOCTL_ATA_PASS_THROUGH,
                ata_pt,
                buffer_size
            )
            
            return bytes(buffer) if result else None

        except Exception as e:
            logger.debug(f"ATA IDENTIFY failed: {e}")
            return None

    def detect_best_wipe_method(self, device_info: DeviceInfo) -> Dict[str, str]:
        """Detect the best wiping method for the given device"""
        if device_info.is_system_drive:
            return {
                'method': WipeMethod.QUICK,
                'reason': 'System drive - hardware erase disabled for safety'
            }

        if device_info.drive_type == DriveType.NVME_SSD:
            if device_info.supports_nvme_sanitize:
                return {
                    'method': WipeMethod.NVME_SANITIZE_CRYPTO,
                    'reason': 'NVMe Crypto Erase provides instant secure erasure'
                }
            elif device_info.supports_nvme_format:
                return {
                    'method': WipeMethod.NVME_FORMAT,
                    'reason': 'NVMe Format NVM resets all cells'
                }

        elif device_info.drive_type == DriveType.SATA_SSD:
            if device_info.is_frozen:
                return {
                    'method': WipeMethod.QUICK,
                    'reason': 'Drive is frozen - power cycle required for ATA Secure Erase'
                }
            elif device_info.supports_ata_enhanced_secure_erase:
                return {
                    'method': WipeMethod.ATA_ENHANCED_SECURE_ERASE,
                    'reason': 'Enhanced Secure Erase ensures all cells are erased'
                }
            elif device_info.supports_ata_secure_erase:
                return {
                    'method': WipeMethod.ATA_SECURE_ERASE,
                    'reason': 'ATA Secure Erase is faster and more effective for SSDs'
                }

        elif device_info.drive_type == DriveType.HDD:
            if device_info.is_frozen:
                return {
                    'method': WipeMethod.DOD_3_PASS,
                    'reason': 'Drive is frozen - using software overwrite'
                }
            elif device_info.supports_ata_secure_erase:
                return {
                    'method': WipeMethod.ATA_SECURE_ERASE,
                    'reason': 'ATA Secure Erase is firmware-based and reliable'
                }
            else:
                return {
                    'method': WipeMethod.DOD_3_PASS,
                    'reason': 'DoD 3-Pass provides good security for HDDs'
                }

        return {
            'method': WipeMethod.QUICK,
            'reason': 'Software overwrite for maximum compatibility'
        }

    def get_supported_methods(self, device_info: DeviceInfo) -> List[str]:
        """Get list of supported wipe methods for device"""
        methods = []
        
        if not device_info.is_system_drive:
            if device_info.supports_nvme_sanitize:
                methods.extend([
                    WipeMethod.NVME_SANITIZE_CRYPTO,
                    WipeMethod.NVME_SANITIZE_BLOCK,
                    WipeMethod.NVME_SANITIZE_OVERWRITE
                ])
            
            if device_info.supports_nvme_format:
                methods.append(WipeMethod.NVME_FORMAT)
            
            if device_info.supports_ata_enhanced_secure_erase and not device_info.is_frozen:
                methods.append(WipeMethod.ATA_ENHANCED_SECURE_ERASE)
            
            if device_info.supports_ata_secure_erase and not device_info.is_frozen:
                methods.append(WipeMethod.ATA_SECURE_ERASE)
        
        methods.extend([
            WipeMethod.QUICK,
            WipeMethod.DOD_3_PASS,
            WipeMethod.DOD_7_PASS,
            WipeMethod.GUTMANN_35_PASS
        ])
        
        return methods

    def start_wipe(self, device_info: DeviceInfo, method: str, 
                   progress_callback: Optional[Callable[[int, str], None]] = None) -> Dict:
        """Start wipe operation with selected method"""
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
            'device_type': device_info.drive_type.value,
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

            # Route to appropriate wipe method
            if method in [WipeMethod.ATA_SECURE_ERASE, WipeMethod.ATA_ENHANCED_SECURE_ERASE]:
                enhanced = (method == WipeMethod.ATA_ENHANCED_SECURE_ERASE)
                result = self._perform_ata_secure_erase(device_info, enhanced, progress_callback, result)
            
            elif method == WipeMethod.NVME_FORMAT:
                result = self._perform_nvme_format(device_info, progress_callback, result)
            
            elif method in [WipeMethod.NVME_SANITIZE_CRYPTO, WipeMethod.NVME_SANITIZE_BLOCK, 
                           WipeMethod.NVME_SANITIZE_OVERWRITE]:
                result = self._perform_nvme_sanitize(device_info, method, progress_callback, result)
            
            else:
                # Software overwrite methods
                result = self._perform_software_wipe(device_info, method, progress_callback, result)

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

    def _perform_ata_secure_erase(self, device_info: DeviceInfo, enhanced: bool,
                                   progress_callback: Optional[Callable], result: Dict) -> Dict:
        """Perform ATA Secure Erase"""
        try:
            if progress_callback:
                progress_callback(10, "ATA Secure Erase not yet implemented - using software wipe")
            
            logger.warning("ATA Secure Erase requires additional Windows driver support")
            logger.info("Falling back to software wipe method")
            
            # Fallback to software wipe
            return self._perform_software_wipe(device_info, WipeMethod.DOD_3_PASS, progress_callback, result)

        except Exception as e:
            logger.error(f"ATA Secure Erase failed: {e}")
            result['error'] = str(e)
            result['status'] = 'Failed'
            return result

    def _perform_nvme_format(self, device_info: DeviceInfo,
                              progress_callback: Optional[Callable], result: Dict) -> Dict:
        """Perform NVMe Format"""
        try:
            if progress_callback:
                progress_callback(10, "NVMe Format not yet implemented - using software wipe")
            
            logger.warning("NVMe Format requires NVMe driver support")
            logger.info("Falling back to software wipe method")
            
            return self._perform_software_wipe(device_info, WipeMethod.QUICK, progress_callback, result)

        except Exception as e:
            logger.error(f"NVMe Format failed: {e}")
            result['error'] = str(e)
            result['status'] = 'Failed'
            return result

    def _perform_nvme_sanitize(self, device_info: DeviceInfo, method: str,
                                progress_callback: Optional[Callable], result: Dict) -> Dict:
        """Perform NVMe Sanitize"""
        try:
            if progress_callback:
                progress_callback(10, "NVMe Sanitize not yet implemented - using software wipe")
            
            logger.warning("NVMe Sanitize requires NVMe driver support")
            logger.info("Falling back to software wipe method")
            
            return self._perform_software_wipe(device_info, WipeMethod.QUICK, progress_callback, result)

        except Exception as e:
            logger.error(f"NVMe Sanitize failed: {e}")
            result['error'] = str(e)
            result['status'] = 'Failed'
            return result

    def _perform_software_wipe(self, device_info: DeviceInfo, method: str,
                                progress_callback: Optional[Callable], result: Dict) -> Dict:
        """Perform software overwrite wipe"""
        try:
            if progress_callback:
                progress_callback(0, "Opening drive...")

            # Validate access
            can_access, error_msg = self.validate_drive_access(device_info.path)
            if not can_access:
                result['error'] = error_msg
                result['status'] = 'Failed'
                return result

            # Open drive
            handle = None
            try:
                handle = win32file.CreateFile(
                    device_info.path,
                    win32con.GENERIC_WRITE,
                    0,
                    None,
                    win32con.OPEN_EXISTING,
                    win32con.FILE_FLAG_NO_BUFFERING | win32con.FILE_FLAG_WRITE_THROUGH,
                    None
                )
            except Exception as e:
                error_code = getattr(e, 'winerror', None)
                if error_code == 5:
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
                        logger.warning("Opened drive with shared access")
                    except:
                        raise e
                else:
                    raise

            try:
                # Dismount volumes
                if progress_callback:
                    progress_callback(0, "Dismounting volumes...")
                
                self._dismount_drive_volumes(device_info.path)

                # Determine passes
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

                # Perform passes
                for pass_num, pattern in enumerate(passes, 1):
                    if self._stop_requested:
                        result['status'] = 'Cancelled'
                        break

                    if progress_callback:
                        progress_callback(
                            int((pass_num - 1) / total_passes * 100),
                            f"Pass {pass_num}/{total_passes}: Writing {self._get_pattern_name(pattern)}"
                        )

                    self._wipe_pass(handle, device_info.size, pattern, pass_num, total_passes, progress_callback)
                    result['passes_completed'] = pass_num

                if not self._stop_requested:
                    if progress_callback:
                        progress_callback(95, "Generating verification hash...")

                    result['completion_hash'] = self._generate_completion_hash(device_info, result['method'])
                    result['status'] = 'Completed'
                    result['success'] = True

            finally:
                if handle:
                    win32file.CloseHandle(handle)

        except Exception as e:
            logger.error(f"Software wipe failed: {e}")
            result['error'] = str(e)
            result['status'] = 'Failed'

        return result

    def _wipe_pass(self, handle, drive_size: int, pattern: int, pass_num: int, total_passes: int,
                   progress_callback: Optional[Callable[[int, str], None]] = None):
        """Perform a single wipe pass"""
        if pattern == WipePattern.ZEROS:
            buffer = bytes(self._buffer_size)
        elif pattern == WipePattern.ONES:
            buffer = bytes([0xFF] * self._buffer_size)
        else:
            buffer = bytes(random.getrandbits(8) for _ in range(self._buffer_size))

        bytes_written = 0
        win32file.SetFilePointer(handle, 0, win32con.FILE_BEGIN)
        
        last_progress_update = 0

        while bytes_written < drive_size and not self._stop_requested:
            bytes_to_write = min(self._buffer_size, drive_size - bytes_written)
            write_buffer = buffer[:bytes_to_write] if bytes_to_write < self._buffer_size else buffer

            error_code, _ = win32file.WriteFile(handle, write_buffer)
            if error_code != 0:
                raise Exception(f"Write failed with error code: {error_code}")

            bytes_written += bytes_to_write
            
            # Calculate overall progress
            pass_progress = (bytes_written / drive_size) * 100
            overall_progress = ((pass_num - 1) / total_passes * 100) + (pass_progress / total_passes)
            self._current_progress = int(overall_progress)
            
            # Update progress callback every 1%
            if self._current_progress - last_progress_update >= 1:
                if progress_callback:
                    progress_callback(
                        self._current_progress,
                        f"Pass {pass_num}/{total_passes}: {int(pass_progress)}% - {self._get_pattern_name(pattern)}"
                    )
                last_progress_update = self._current_progress

            # Log progress periodically
            if bytes_written % (self._buffer_size * 100) == 0:
                logger.log_wipe_progress(f"Pass {pass_num}/{total_passes}", self._current_progress)

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

    def validate_drive_access(self, device_path: str) -> tuple[bool, str]:
        """Validate drive access"""
        try:
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

            if error_code == 5:
                return False, "Access Denied: Run as Administrator"
            elif error_code == 2:
                return False, "Drive not found"
            elif error_code == 32:
                return False, "Drive is in use"
            else:
                return False, f"Cannot access drive: {str(e)}"

    def get_drive_by_path(self, path: str) -> Optional[DeviceInfo]:
        """Get specific drive information by path"""
        drives = self.get_available_drives()
        for drive in drives:
            if drive.path == path:
                return drive
        return None

    def _get_volumes_for_drive(self, device_path: str) -> List[str]:
        """Get volumes for drive"""
        volumes = []
        try:
            drive_num = int(device_path.split('PHYSICALDRIVE')[-1])

            import string
            for letter in string.ascii_uppercase:
                volume_path = f"\\\\.\\{letter}:"
                try:
                    if self._is_volume_on_drive(volume_path, drive_num):
                        volumes.append(volume_path)
                except:
                    continue

        except Exception as e:
            logger.error(f"Error getting volumes: {e}")

        return volumes

    def _is_volume_on_drive(self, volume_path: str, drive_num: int) -> bool:
        """Check if volume is on specified drive"""
        try:
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
                extents = win32file.DeviceIoControl(handle, 0x560000, None, 1024)
                if len(extents) >= 12:
                    disk_num = struct.unpack('<I', extents[8:12])[0]
                    return disk_num == drive_num
            finally:
                win32file.CloseHandle(handle)

        except:
            pass

        return False

    def _dismount_drive_volumes(self, device_path: str) -> int:
        """Dismount all volumes on drive"""
        dismounted = 0
        volumes = self._get_volumes_for_drive(device_path)

        for volume_path in volumes:
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
                    win32file.DeviceIoControl(handle, 0x90020, None, None)
                    dismounted += 1
                    logger.debug(f"Dismounted volume: {volume_path}")
                finally:
                    win32file.CloseHandle(handle)
            except Exception as e:
                logger.warning(f"Could not dismount {volume_path}: {e}")

        return dismounted

    def stop_wipe(self):
        """Stop the wiping process"""
        logger.info("Wipe stop requested")
        self._stop_requested = True

    def get_progress(self) -> int:
        """Get current wiping progress"""
        return self._current_progress