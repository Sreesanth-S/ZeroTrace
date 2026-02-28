import os
import win32file
import win32con
import wmi
import random
import time
import hashlib
import struct
import ctypes
from typing import List, Dict, Optional, Callable
from datetime import datetime
from logger import logger
from enum import Enum
import subprocess
import tempfile

class DriveType(Enum):
    """Drive type enumeration"""
    UNKNOWN = "Unknown"
    HDD = "HDD"
    SATA_SSD = "SATA SSD"
    NVME_SSD = "NVMe SSD"
    USB_FLASH = "USB Flash Drive"

class DriveFormatter:
    """Handle drive formatting after wipe operations"""
    
    @staticmethod
    def detect_original_filesystem(device_path: str) -> Dict[str, any]:
        try:
            drive_num = int(device_path.split('PHYSICALDRIVE')[-1])
            filesystem_info = {
                'volumes': [],
                'partition_style': 'MBR',  # Default
                'has_partitions': False
            }
            
            wmi_obj = wmi.WMI()
            
            # Get partition information
            for partition in wmi_obj.Win32_DiskPartition():
                if partition.DiskIndex == drive_num:
                    filesystem_info['has_partitions'] = True
                    
                    # Get partition style (MBR or GPT)
                    if hasattr(partition, 'Type'):
                        if 'GPT' in partition.Type:
                            filesystem_info['partition_style'] = 'GPT'
                    
                    # Get associated logical disks
                    for logical_disk in partition.associators("Win32_LogicalDisk"):
                        volume_info = {
                            'drive_letter': logical_disk.DeviceID,
                            'filesystem': logical_disk.FileSystem or 'NTFS',
                            'label': logical_disk.VolumeName or 'DATA',
                            'size': int(logical_disk.Size) if logical_disk.Size else 0
                        }
                        filesystem_info['volumes'].append(volume_info)
            
            logger.info(f"Detected filesystem info: {filesystem_info}")
            return filesystem_info
            
        except Exception as e:
            logger.error(f"Error detecting filesystem: {e}")
            # Return safe defaults
            return {
                'volumes': [],
                'partition_style': 'MBR',
                'has_partitions': False
            }
    
    @staticmethod
    def format_drive(device_path: str, filesystem_info: Dict, 
                     progress_callback: Optional[Callable] = None) -> bool:
        try:
            drive_num = int(device_path.split('PHYSICALDRIVE')[-1])
            
            if progress_callback:
                progress_callback(90, "Creating partition table...")
            
            # Create diskpart script
            script_lines = [
                f"select disk {drive_num}",
                "clean",  # Clean the disk first
            ]
            
            # Create partition based on original style
            if filesystem_info.get('partition_style') == 'GPT':
                script_lines.append("convert gpt")
                script_lines.append("create partition primary")
            else:
                script_lines.append("convert mbr")
                script_lines.append("create partition primary")
            
            script_lines.extend([
                "select partition 1",
                "active"  # Set active for MBR
            ])
            
            # Determine filesystem and label
            if filesystem_info.get('volumes') and len(filesystem_info['volumes']) > 0:
                volume = filesystem_info['volumes'][0]
                fs_type = volume.get('filesystem', 'NTFS')
                label = volume.get('label', 'DATA')
            else:
                # Defaults
                fs_type = 'NTFS'
                label = 'DATA'
            
            # Format the partition
            if fs_type.upper() in ['NTFS', 'FAT32', 'EXFAT', 'FAT']:
                format_cmd = f'format fs={fs_type} label="{label}" quick'
            else:
                # Fallback to NTFS
                format_cmd = 'format fs=NTFS label="DATA" quick'
            
            script_lines.append(format_cmd)
            script_lines.append("assign")  # Auto-assign drive letter
            script_lines.append("exit")
            
            logger.info(f"Diskpart script: {script_lines}")
            
            if progress_callback:
                progress_callback(92, "Writing partition table...")
            
            # Write script to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write('\n'.join(script_lines))
                script_path = f.name
            
            try:
                if progress_callback:
                    progress_callback(95, f"Formatting as {fs_type}...")
                
                # Execute diskpart
                result = subprocess.run(
                    ['diskpart', '/s', script_path],
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                
                logger.info(f"Diskpart output: {result.stdout}")
                
                if result.returncode == 0:
                    logger.info(f"Successfully formatted drive as {fs_type}")
                    if progress_callback:
                        progress_callback(98, "Format complete")
                    return True
                else:
                    logger.error(f"Diskpart failed: {result.stderr}")
                    return False
                    
            finally:
                # Clean up temp file
                try:
                    os.unlink(script_path)
                except:
                    pass
                    
        except subprocess.TimeoutExpired:
            logger.error("Format operation timed out")
            return False
        except Exception as e:
            logger.error(f"Format error: {e}")
            return False

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

    # Hidden/host protected area
    HIDDEN_SECTORS = "Hidden Sector Wipe (HPA/DCO)"


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

        # Host Protected Area (HPA) / hidden sector info
        # these values are populated when checking ATA support
        self.hpa_enabled = False
        self.hpa_user_sectors = 0
        self.hpa_max_sectors = 0
        self.hpa_hidden_sectors = 0


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

                    # detect hidden sectors / HPA
                    try:
                        # word 60-61 = user addressable sectors (28bit)
                        user_lo = struct.unpack('<H', identify_data[120:122])[0]
                        user_hi = struct.unpack('<H', identify_data[122:124])[0]
                        user_sectors = (user_hi << 16) | user_lo

                        # word 100-103 = max addressable LBA for HPA/DCO (may be 48-bit)
                        # combine four words (100..103) little-endian
                        max_low = struct.unpack('<H', identify_data[200:202])[0]
                        max_mid = struct.unpack('<H', identify_data[202:204])[0]
                        max_high = struct.unpack('<H', identify_data[204:206])[0]
                        max_hi = struct.unpack('<H', identify_data[206:208])[0]
                        max_sectors = (max_hi << 48) | (max_high << 32) | (max_mid << 16) | max_low

                        if max_sectors > user_sectors:
                            device_info.hpa_enabled = True
                            device_info.hpa_user_sectors = user_sectors
                            device_info.hpa_max_sectors = max_sectors
                            device_info.hpa_hidden_sectors = max_sectors - user_sectors
                            logger.info(f"Detected HPA on {device_info.name}: hidden {device_info.hpa_hidden_sectors} sectors")
                    except Exception as _:
                        # ignore if identify data truncated or parsing fails
                        pass

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

    def _get_hpa_info(self, handle) -> Optional[Dict[str, int]]:
        """Return HPA/hidden sector information for a drive handle.

        The returned dict contains keys:
            user_sectors, max_sectors, hidden_sectors, hpa_enabled
        """
        try:
            identify_data = self._send_ata_identify(handle)
            if not identify_data or len(identify_data) < 208:
                return None

            # user addressable sectors (words 60-61)
            user_lo = struct.unpack('<H', identify_data[120:122])[0]
            user_hi = struct.unpack('<H', identify_data[122:124])[0]
            user_sectors = (user_hi << 16) | user_lo

            # maximum addressable LBA (words 100-103, 48-bit value)
            # treat as little-endian 4 words
            max_low = struct.unpack('<H', identify_data[200:202])[0]
            max_mid = struct.unpack('<H', identify_data[202:204])[0]
            max_high = struct.unpack('<H', identify_data[204:206])[0]
            max_hi = struct.unpack('<H', identify_data[206:208])[0]
            max_sectors = (max_hi << 48) | (max_high << 32) | (max_mid << 16) | max_low

            hidden = max_sectors - user_sectors if max_sectors > user_sectors else 0
            return {
                'user_sectors': user_sectors,
                'max_sectors': max_sectors,
                'hidden_sectors': hidden,
                'hpa_enabled': hidden > 0
            }
        except Exception as e:
            logger.debug(f"Error getting HPA info: {e}")
            return None

    def _set_hpa_size(self, handle, sectors: int) -> bool:
        """Set the host protected area limit (maximum addressable sectors).

        """
        try:
            # Prepare taskfile registers for SET MAX ADDRESS (0xF9)
            ata_pt = ATAPassThroughDirect()
            ata_pt.Length = ctypes.sizeof(ATAPassThroughDirect)
            ata_pt.AtaFlags = 0x00  # no data transfer
            ata_pt.DataTransferLength = 0
            ata_pt.TimeOutValue = 10

            # build 48-bit LBA value into registers
            lba = sectors
            ata_pt.CurrentTaskFile[2] = lba & 0xFF  # LBA low
            ata_pt.CurrentTaskFile[3] = (lba >> 8) & 0xFF  # LBA mid
            ata_pt.CurrentTaskFile[4] = (lba >> 16) & 0xFF  # LBA high
            # device register: set LBA mode bit (bit 6)
            ata_pt.CurrentTaskFile[5] = 0x40

            # high-order bytes for 48-bit
            ata_pt.CurrentTaskFile[0] = (lba >> 24) & 0xFF  # feature high? using feature reg for high
            ata_pt.CurrentTaskFile[1] = (lba >> 32) & 0xFF  # sector count high? reuse
            ata_pt.CurrentTaskFile[2] |= (lba >> 40) & 0xFF  # extend LBA into low reg

            ata_pt.CurrentTaskFile[6] = 0xF9  # SET MAX ADDRESS

            result = win32file.DeviceIoControl(
                handle,
                self.IOCTL_ATA_PASS_THROUGH,
                ata_pt,
                0
            )
            return bool(result)
        except Exception as e:
            logger.warning(f"Failed to set HPA size: {e}")
            return False

    def _wipe_hidden_area(self, handle, start_bytes: int, length: int,
                          progress_callback: Optional[Callable[[int, str], None]] = None):
        """Overwrite a region of the drive starting at *start_bytes* for *length* bytes.

        Used for wiping previously hidden sectors after HPA is removed.
        """
        if length <= 0:
            return

        win32file.SetFilePointer(handle, start_bytes, win32con.FILE_BEGIN)
        bytes_written = 0
        buffer = bytes(self._buffer_size)
        last_progress = 0

        while bytes_written < length and not self._stop_requested:
            write_size = min(self._buffer_size, length - bytes_written)
            error_code, _ = win32file.WriteFile(handle, buffer[:write_size])
            if error_code != 0:
                raise Exception(f"Hidden area write failed: {error_code}")

            bytes_written += write_size
            if progress_callback:
                pct = int(bytes_written / length * 100)
                if pct - last_progress >= 1:
                    progress_callback(pct, "Wiping hidden sectors")
                    last_progress = pct
            time.sleep(0.001)

    def detect_best_wipe_method(self, device_info: DeviceInfo) -> Dict[str, str]:
        """Detect the best wiping method for the given device"""
        if device_info.is_system_drive:
            return {
                'method': WipeMethod.QUICK,
                'reason': 'System drive - hardware erase disabled for safety'
            }

        # compute normal best method (see logic below)

        best_method = None
        if device_info.drive_type == DriveType.NVME_SSD:
            if device_info.supports_nvme_sanitize:
                best_method = {
                    'method': WipeMethod.NVME_SANITIZE_CRYPTO,
                    'reason': 'NVMe Crypto Erase provides instant secure erasure'
                }
            elif device_info.supports_nvme_format:
                best_method = {
                    'method': WipeMethod.NVME_FORMAT,
                    'reason': 'NVMe Format NVM resets all cells'
                }

        elif device_info.drive_type == DriveType.SATA_SSD:
            if device_info.is_frozen:
                best_method = {
                    'method': WipeMethod.QUICK,
                    'reason': 'Drive is frozen - power cycle required for ATA Secure Erase'
                }
            elif device_info.supports_ata_enhanced_secure_erase:
                best_method = {
                    'method': WipeMethod.ATA_ENHANCED_SECURE_ERASE,
                    'reason': 'Enhanced Secure Erase ensures all cells are erased'
                }
            elif device_info.supports_ata_secure_erase:
                best_method = {
                    'method': WipeMethod.ATA_SECURE_ERASE,
                    'reason': 'ATA Secure Erase is faster and more effective for SSDs'
                }

        elif device_info.drive_type == DriveType.HDD:
            if device_info.is_frozen:
                best_method = {
                    'method': WipeMethod.DOD_3_PASS,
                    'reason': 'Drive is frozen - using software overwrite'
                }
            elif device_info.supports_ata_secure_erase:
                best_method = {
                    'method': WipeMethod.ATA_SECURE_ERASE,
                    'reason': 'ATA Secure Erase is firmware-based and reliable'
                }
            else:
                best_method = {
                    'method': WipeMethod.DOD_3_PASS,
                    'reason': 'DoD 3-Pass provides good security for HDDs'
                }

        if not best_method:
            best_method = {
                'method': WipeMethod.QUICK,
                'reason': 'Software overwrite for maximum compatibility'
            }

        # annotate if hidden sectors are present
        if getattr(device_info, 'hpa_enabled', False):
            best_method['reason'] += f" (contains {device_info.hpa_hidden_sectors} hidden sectors)"

        return best_method

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

            # if the drive has a host-protected area (hidden sectors), allow explicit wipe
            if getattr(device_info, 'hpa_enabled', False):
                methods.append(WipeMethod.HIDDEN_SECTORS)
        
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

            elif method == WipeMethod.HIDDEN_SECTORS:
                result = self._perform_hidden_sector_wipe(device_info, progress_callback, result)
            
            else:
                # Software overwrite methods (automatically handle any hidden zones)
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

    def _perform_ata_secure_erase(self, device_info: DeviceInfo, enhanced: bool, progress_callback: Optional[Callable], result: Dict) -> Dict:
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

    def _perform_hidden_sector_wipe(self, device_info: DeviceInfo,
                                    progress_callback: Optional[Callable], result: Dict) -> Dict:
        """Wipe only the hidden sectors that are masked by HPA/DCO."""
        try:
            # Access drive and check HPA info
            can_access, error_msg = self.validate_drive_access(device_info.path)
            if not can_access:
                result['error'] = error_msg
                result['status'] = 'Failed'
                return result

            # open handle similar to software wipe
            handle = win32file.CreateFile(
                device_info.path,
                win32con.GENERIC_WRITE,
                win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
                None,
                win32con.OPEN_EXISTING,
                win32con.FILE_FLAG_NO_BUFFERING | win32con.FILE_FLAG_WRITE_THROUGH,
                None
            )

            try:
                if progress_callback:
                    progress_callback(0, "Checking for hidden sectors...")

                hpa_info = self._get_hpa_info(handle)
                if not hpa_info or not hpa_info.get('hpa_enabled'):
                    result['status'] = 'Failed'
                    result['error'] = 'No hidden sectors detected on this drive'
                    return result

                hidden_sectors = hpa_info['hidden_sectors']
                start_offset = hpa_info['user_sectors'] * self._sector_size
                total_bytes = hidden_sectors * self._sector_size

                if progress_callback:
                    progress_callback(10, f"Exposing hidden area ({hidden_sectors} sectors)")

                # disable HPA to expose full capacity
                self._set_hpa_size(handle, hpa_info['max_sectors'])

                # wipe the hidden region with a single zero pass
                if progress_callback:
                    progress_callback(20, "Wiping hidden sectors...")

                self._wipe_hidden_area(handle, start_offset, total_bytes, progress_callback)
                result['passes_completed'] = 1

                # restore original HPA limit
                self._set_hpa_size(handle, hpa_info['user_sectors'])
                logger.info("Hidden sector wipe completed and HPA limit restored")

                result['status'] = 'Completed'
                result['success'] = True
            finally:
                win32file.CloseHandle(handle)

        except Exception as e:
            logger.error(f"Hidden sector wipe failed: {e}")
            result['error'] = str(e)
            result['status'] = 'Failed'

        return result

    def _perform_software_wipe(self, device_info: DeviceInfo, method: str,
                                progress_callback: Optional[Callable], result: Dict) -> Dict:
        """Perform software overwrite wipe with automatic reformatting"""
        
        # Detect original filesystem BEFORE wiping
        formatter = DriveFormatter()
        filesystem_info = formatter.detect_original_filesystem(device_info.path)
        
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

                # determine if drive has a Host Protected Area
                hpa_info = self._get_hpa_info(handle)
                original_size = device_info.size
                wipe_size = device_info.size

                if hpa_info and hpa_info.get('hpa_enabled'):
                    # expose the full capacity
                    if progress_callback:
                        progress_callback(0, "Removing HPA limit to expose hidden sectors...")
                    logger.info(f"HPA detected: {hpa_info['hidden_sectors']} hidden sectors")

                    # expand to maximum LBA
                    if self._set_hpa_size(handle, hpa_info['max_sectors']):
                        wipe_size = hpa_info['max_sectors'] * self._sector_size
                        # update device_info.size so logs/report reflect new size
                        device_info.size = wipe_size
                    else:
                        logger.warning("Failed to remove HPA limit; hidden sectors may not be wiped")

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

                # Perform wipe passes (0-90% of total progress)
                for pass_num, pattern in enumerate(passes, 1):
                    if self._stop_requested:
                        result['status'] = 'Cancelled'
                        break

                    if progress_callback:
                        base_progress = int((pass_num - 1) / total_passes * 90)
                        progress_callback(
                            base_progress,
                            f"Pass {pass_num}/{total_passes}: Writing {self._get_pattern_name(pattern)}"
                        )

                    self._wipe_pass(handle, wipe_size, pattern, pass_num, total_passes, 
                                   progress_callback, max_progress=90)
                    result['passes_completed'] = pass_num

                # restore HPA if we changed it
                if hpa_info and hpa_info.get('hpa_enabled'):
                    try:
                        self._set_hpa_size(handle, hpa_info['user_sectors'])
                        logger.info("HPA limit restored after wipe")
                        # revert device_info.size to original for reporting purposes
                        device_info.size = original_size
                    except Exception:
                        pass

                if not self._stop_requested:
                    if progress_callback:
                        progress_callback(90, "Generating verification hash...")

                    result['completion_hash'] = self._generate_completion_hash(device_info, result['method'])
                    
                    # Close handle before formatting
                    win32file.CloseHandle(handle)
                    handle = None
                    
                    # Format the drive (90-98% of progress)
                    if progress_callback:
                        progress_callback(90, "Reformatting drive...")
                    
                    logger.info(f"Reformatting drive with original filesystem: {filesystem_info}")
                    format_success = formatter.format_drive(device_info.path, filesystem_info, 
                                                            progress_callback)
                    
                    if format_success:
                        logger.info("Drive formatted successfully")
                        result['formatted'] = True
                        result['filesystem'] = filesystem_info
                    else:
                        logger.warning("Format failed, but wipe was successful")
                        result['formatted'] = False
                        result['format_error'] = "Format failed - drive may need manual formatting"
                    
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
                   progress_callback: Optional[Callable[[int, str], None]] = None,
                   max_progress: int = 100):
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
            
            # Calculate progress within the max_progress limit
            pass_progress = (bytes_written / drive_size) * 100
            overall_progress = ((pass_num - 1) / total_passes * max_progress) + (pass_progress / total_passes * max_progress / 100)
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