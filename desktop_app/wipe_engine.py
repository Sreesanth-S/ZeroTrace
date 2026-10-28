import os
import win32file
import win32con
import wmi
import time
import hashlib
import struct
import ctypes
from typing import List, Dict, Optional, Callable
from pathlib import Path
from datetime import datetime
import logging
logger = logging.getLogger("ZeroTrace")
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
        """
        Format drive using native PowerShell storage cmdlets with fallback to diskpart.
        """
        try:
            drive_num = int(device_path.split('PHYSICALDRIVE')[-1])
            
            if progress_callback:
                progress_callback(90, "Creating partition table...")
            
            partition_style = filesystem_info.get('partition_style', 'MBR').upper()
            if partition_style not in ['GPT', 'MBR']:
                partition_style = 'MBR'
            
            if filesystem_info.get('volumes') and len(filesystem_info['volumes']) > 0:
                volume = filesystem_info['volumes'][0]
                fs_type = volume.get('filesystem', 'NTFS').upper()
                label = volume.get('label', 'DATA')
            else:
                fs_type = 'NTFS'
                label = 'DATA'

            if fs_type not in ['NTFS', 'FAT32', 'EXFAT']:
                fs_type = 'NTFS'

            # Strategy 1: Try PowerShell Storage Cmdlets (native Windows Storage API)
            try:
                if progress_callback:
                    progress_callback(92, f"Initializing disk via PowerShell ({fs_type})...")
                
                ps_commands = (
                    f"Clear-Disk -Number {drive_num} -RemoveData -Confirm:$false -ErrorAction SilentlyContinue; "
                    f"Initialize-Disk -Number {drive_num} -PartitionStyle {partition_style} -ErrorAction Stop; "
                    f"$p = New-Partition -DiskNumber {drive_num} -UseMaximumSize -AssignDriveLetter -ErrorAction Stop; "
                    f"Format-Volume -Partition $p -FileSystem {fs_type} -NewFileSystemLabel '{label}' -Confirm:$false -ErrorAction Stop"
                )
                
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_commands],
                    capture_output=True,
                    text=True,
                    timeout=180
                )
                
                if result.returncode == 0:
                    logger.info(f"Successfully formatted drive {drive_num} via PowerShell as {fs_type}")
                    if progress_callback:
                        progress_callback(98, "Format complete")
                    return True
                else:
                    logger.warning(f"PowerShell format stderr: {result.stderr.strip()}, falling back to diskpart...")
            except Exception as ps_err:
                logger.warning(f"PowerShell format exception: {ps_err}, falling back to diskpart...")

            # Strategy 2: Fallback to Diskpart script execution
            if progress_callback:
                progress_callback(94, "Formatting drive via Diskpart fallback...")

            script_lines = [
                f"select disk {drive_num}",
                "clean",
                f"convert {partition_style.lower()}",
                "create partition primary",
                "select partition 1",
                "active" if partition_style == 'MBR' else "",
                f'format fs={fs_type} label="{label}" quick',
                "assign",
                "exit"
            ]
            script_lines = [line for line in script_lines if line]

            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write('\n'.join(script_lines))
                script_path = f.name

            try:
                result = subprocess.run(
                    ['diskpart', '/s', script_path],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                
                if result.returncode == 0:
                    logger.info(f"Successfully formatted drive {drive_num} via Diskpart fallback as {fs_type}")
                    if progress_callback:
                        progress_callback(98, "Format complete")
                    return True
                else:
                    logger.error(f"Diskpart fallback failed: {result.stderr}")
                    return False
            finally:
                try:
                    os.unlink(script_path)
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"Format error on {device_path}: {e}")
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

    # Hidden/host protected area
    HIDDEN_SECTORS = "Hidden Sector Wipe (HPA/DCO)"


def get_compliance_info(method: str, is_fallback: bool = False) -> dict:
    """
    Returns structured compliance mapping for a given wipe method.
    Maps algorithms to NIST SP 800-88 Rev 1, IEEE 2883-2022, and DoD 5220.22-M standards.

    Args:
        method: The wipe method identifier.
        is_fallback: If True, the hardware method was not actually executed and
                     a software fallback was used instead.  The compliance level
                     is downgraded to reflect reality.
    """
    hardware_methods = [
        WipeMethod.ATA_SECURE_ERASE,
        WipeMethod.ATA_ENHANCED_SECURE_ERASE,
        WipeMethod.NVME_FORMAT,
        WipeMethod.NVME_SANITIZE_CRYPTO,
        WipeMethod.NVME_SANITIZE_BLOCK,
        WipeMethod.NVME_SANITIZE_OVERWRITE
    ]

    if method in hardware_methods and not is_fallback:
        level = "Purge"
        nist_status = "NIST SP 800-88 Rev 1 Purge"
        ieee_status = "IEEE 2883-2022 Purge"
        dod_status = "N/A (Hardware Purge Exceeds DoD Overwrite)"
        description = "Hardware controller-level sanitization addressing user-accessible and non-accessible physical memory areas."
        implemented = True
    elif method in hardware_methods and is_fallback:
        # Honest labelling: hardware method was requested but not executed
        level = "Clear (Software Fallback)"
        nist_status = "NIST SP 800-88 Rev 1 Clear (hardware erase unavailable)"
        ieee_status = "IEEE 2883-2022 Clear (software overwrite only)"
        dod_status = "Software Overwrite Fallback"
        description = ("Hardware erasure was requested but is not yet implemented. "
                       "A software overwrite was performed instead. This does NOT "
                       "reach over-provisioned blocks or controller-managed areas.")
        implemented = False
    elif method in [WipeMethod.DOD_3_PASS, WipeMethod.DOD_7_PASS]:
        level = "Clear"
        nist_status = "NIST SP 800-88 Rev 1 Clear"
        ieee_status = "IEEE 2883-2022 Clear"
        dod_status = "DoD 5220.22-M Compliant"
        description = "Software logical overwriting across all user-accessible storage locations using multi-pass patterns."
        implemented = True
    elif method == WipeMethod.HIDDEN_SECTORS:
        level = "Purge Extension"
        nist_status = "NIST SP 800-88 Rev 1 Hidden Sector Purge"
        ieee_status = "IEEE 2883-2022 Hidden Area Clear/Purge"
        dod_status = "HPA/DCO Unlocks & Wipes"
        description = "Targeted un-hiding and sanitization of Host Protected Area (HPA) and Device Configuration Overlay (DCO) sectors."
        implemented = True
    else:  # Quick Wipe or default
        level = "Clear"
        nist_status = "NIST SP 800-88 Rev 1 Clear"
        ieee_status = "IEEE 2883-2022 Clear"
        dod_status = "Basic Logical Overwrite"
        description = "Software logical overwriting across user-accessible storage locations using single-pass zeros."
        implemented = True

    return {
        "level": level,
        "nist_800_88": nist_status,
        "ieee_2883": ieee_status,
        "dod_5220_22_m": dod_status,
        "description": description,
        "implemented": implemented
    }


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


class WipeJournal:
    """Track active wipe operation state in-memory (no disk writing or logs folder creation by default)."""

    def __init__(self, journal_path: Optional[Path] = None):
        self.journal_path = Path(journal_path) if journal_path else None
        self._in_memory_data: Optional[dict] = None
        if self.journal_path:
            self.journal_path.parent.mkdir(parents=True, exist_ok=True)

    def start_journal(self, device_info: DeviceInfo, method: str) -> dict:
        journal_data = {
            'journal_id': f"JNL-{hashlib.sha256(f'{device_info.path}:{datetime.now().isoformat()}'.encode()).hexdigest()[:12].upper()}",
            'device_path': device_info.path,
            'device_name': device_info.name,
            'device_serial': device_info.serial,
            'device_model': device_info.model,
            'device_size': device_info.size,
            'method': method,
            'status': 'IN_PROGRESS',
            'start_time': datetime.now().isoformat(),
            'current_pass': 0,
            'progress_pct': 0,
            'updated_at': datetime.now().isoformat()
        }
        self.save_journal(journal_data)
        logger.info(f"Wipe journal created: {journal_data['journal_id']} for {device_info.name}")
        return journal_data

    def update_progress(self, journal_data: dict, current_pass: int, progress_pct: int):
        journal_data['current_pass'] = current_pass
        journal_data['progress_pct'] = progress_pct
        journal_data['updated_at'] = datetime.now().isoformat()
        self.save_journal(journal_data)

    def complete_journal(self, journal_data: dict, status: str = 'COMPLETED'):
        journal_data['status'] = status
        journal_data['end_time'] = datetime.now().isoformat()
        journal_data['updated_at'] = datetime.now().isoformat()
        self.save_journal(journal_data)
        logger.info(f"Wipe journal closed with status {status}: {journal_data['journal_id']}")

    def save_journal(self, data: dict):
        self._in_memory_data = data
        if self.journal_path:
            try:
                import json
                with open(self.journal_path, 'w') as f:
                    json.dump(data, f, indent=2)
            except Exception as e:
                logger.warning(f"Could not save wipe journal: {e}")

    def load_journal(self) -> Optional[dict]:
        if self.journal_path and self.journal_path.exists():
            try:
                import json
                with open(self.journal_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load wipe journal: {e}")
        return self._in_memory_data

    def clear_journal(self):
        self._in_memory_data = None
        if self.journal_path and self.journal_path.exists():
            try:
                self.journal_path.unlink()
            except Exception as e:
                logger.warning(f"Could not clear wipe journal: {e}")


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


# NVMe command structures for IOCTL_STORAGE_PROTOCOL_COMMAND (0x2D143C)
class StorageProtocolCommand(ctypes.Structure):
    _fields_ = [
        ("Version", ctypes.c_ulong),
        ("Length", ctypes.c_ulong),
        ("ProtocolType", ctypes.c_ulong),
        ("Flags", ctypes.c_ulong),
        ("CommandLength", ctypes.c_ulong),
        ("ErrorInfoLength", ctypes.c_ulong),
        ("DataFromDeviceTransferLength", ctypes.c_ulong),
        ("DataToDeviceTransferLength", ctypes.c_ulong),
        ("TimeOutValue", ctypes.c_ulong),
        ("ErrorInfoOffset", ctypes.c_ulong),
        ("DataFromDeviceBufferOffset", ctypes.c_ulong),
        ("DataToDeviceBufferOffset", ctypes.c_ulong),
        ("CommandSpecific", ctypes.c_ulong * 8),
        ("Reserved0", ctypes.c_ulong * 4),
        ("Command", ctypes.c_ubyte * 64),
    ]


class WipeEngine:
    """Enhanced drive wiping engine with hardware secure erase support"""

    # IOCTL codes
    IOCTL_ATA_PASS_THROUGH = 0x4D02C
    IOCTL_STORAGE_QUERY_PROPERTY = 0x2D1400
    IOCTL_STORAGE_PROTOCOL_COMMAND = 0x2D143C
    
    # ATA commands
    ATA_IDENTIFY_DEVICE = 0xEC
    ATA_SECURITY_SET_PASSWORD = 0xF1
    ATA_SECURITY_UNLOCK = 0xF2
    ATA_SECURITY_ERASE_PREPARE = 0xF3
    ATA_SECURITY_ERASE_UNIT = 0xF4
    ATA_SECURITY_DISABLE_PASSWORD = 0xF6

    # NVMe Admin Opcodes
    NVME_ADMIN_FORMAT_NVM = 0x80
    NVME_ADMIN_SANITIZE = 0x84

    def __init__(self):
        self._stop_requested = False
        self._current_progress = 0
        self._sector_size = 512
        self._buffer_size = 1024 * 1024  # 1MB buffer
        self.wmi = wmi.WMI()
        self._volume_handles = []
        self.journal = WipeJournal()
        self.check_interrupted_wipes()

    def check_interrupted_wipes(self) -> Optional[dict]:
        """Check if a previous wipe operation was interrupted by power-loss or crash."""
        interrupted = self.journal.load_journal()
        if interrupted and interrupted.get('status') == 'IN_PROGRESS':
            logger.warning(
                f"INTERRUPTED WIPE DETECTED: Drive {interrupted.get('device_name')} "
                f"({interrupted.get('device_path')}) was interrupted during pass "
                f"{interrupted.get('current_pass')} ({interrupted.get('progress_pct')}%). "
                f"RESANITIZATION REQUIRED."
            )
            return interrupted
        return None
        
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
            WipeMethod.DOD_7_PASS
        ])
        
        return methods

    def start_wipe(self, device_info: DeviceInfo, method: str, 
                   progress_callback: Optional[Callable[[int, str], None]] = None) -> Dict:
        """Start wipe operation with selected method"""
        self._stop_requested = False
        self._current_progress = 0
        
        start_time = datetime.now()
        
        # Start wipe journal for crash & power-loss recovery
        journal_data = self.journal.start_journal(device_info, method)
        
        result = {
            'success': False,
            'device_id': device_info.path,
            'device_name': device_info.name,
            'device_serial': device_info.serial,
            'device_model': device_info.model,
            'device_size': device_info.size,
            'device_type': device_info.drive_type.value,
            'method': method,
            'compliance': get_compliance_info(method),
            'start_time': start_time.isoformat(),
            'end_time': None,
            'duration': None,
            'status': 'Started',
            'passes_completed': 0,
            'completion_hash': None,
            'error': None,
            'journal_id': journal_data.get('journal_id')
        }
        
        try:
            logger.info(f"Wipe operation started - Device: {device_info.name}, Method: {method}")

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
            logger.error(f"Error during Wipe operation: {e}", exc_info=True)
            result['error'] = str(e)
            result['status'] = 'Failed'

        # Record end time and duration
        end_time = datetime.now()
        result['end_time'] = end_time.isoformat()
        duration = end_time - start_time
        result['duration'] = str(duration)

        # Complete journal
        journal_status = 'COMPLETED' if result['success'] else result['status'].upper()
        self.journal.complete_journal(journal_data, journal_status)

        logger.info(f"Wipe operation completed - Device: {device_info.name}, Status: {result['status']}, Duration: {result['duration']}")

        if progress_callback:
            progress_callback(100, f"Wipe {result['status']}")

        return result

    def _send_ata_security_command(self, handle, command_code: int, password: str = "ZeroTraceErase", enhanced: bool = False) -> bool:
        """Send ATA Security command via IOCTL_ATA_PASS_THROUGH_DIRECT (0x4D02C)."""
        try:
            payload_buffer = ctypes.create_string_buffer(512)
            control_word = 0x0001 if enhanced else 0x0000
            struct.pack_into('<H', payload_buffer, 0, control_word)
            pwd_bytes = password.encode('ascii')[:32].ljust(32, b' ')
            struct.pack_into('32s', payload_buffer, 2, pwd_bytes)

            ata_pt = ATAPassThroughDirect()
            ata_pt.Length = ctypes.sizeof(ATAPassThroughDirect)
            ata_pt.AtaFlags = 0x01  # ATA_FLAGS_DATA_OUT
            ata_pt.DataTransferLength = 512
            ata_pt.TimeOutValue = 30
            ata_pt.DataBufferOffset = ctypes.cast(ctypes.pointer(payload_buffer), ctypes.POINTER(ctypes.c_void_p))
            ata_pt.CurrentTaskFile[6] = command_code
            ata_pt.CurrentTaskFile[7] = 0xA0

            result = win32file.DeviceIoControl(
                handle,
                self.IOCTL_ATA_PASS_THROUGH,
                ata_pt,
                512
            )
            return bool(result)
        except Exception as e:
            logger.debug(f"ATA Security command (0x{command_code:02X}) failed: {e}")
            return False

    def _send_nvme_admin_command(self, handle, opcode: int, cdw10: int = 0, cdw11: int = 0) -> bool:
        """Send NVMe Admin command via IOCTL_STORAGE_PROTOCOL_COMMAND (0x2D143C)."""
        try:
            cmd = StorageProtocolCommand()
            cmd.Version = 1
            cmd.Length = ctypes.sizeof(StorageProtocolCommand)
            cmd.ProtocolType = 1  # ProtocolTypeNvme
            cmd.Flags = 1         # STORAGE_PROTOCOL_COMMAND_FLAG_ADAPTER_COMMAND
            cmd.CommandLength = 64
            cmd.TimeOutValue = 60

            cmd.Command[0] = opcode
            struct.pack_into('<I', cmd.Command, 40, cdw10)
            struct.pack_into('<I', cmd.Command, 44, cdw11)

            result = win32file.DeviceIoControl(
                handle,
                self.IOCTL_STORAGE_PROTOCOL_COMMAND,
                cmd,
                ctypes.sizeof(StorageProtocolCommand)
            )
            return bool(result)
        except Exception as e:
            logger.debug(f"NVMe Admin command (0x{opcode:02X}) failed: {e}")
            return False

    def _perform_ata_secure_erase(self, device_info: DeviceInfo, enhanced: bool, progress_callback: Optional[Callable], result: Dict) -> Dict:
        """Perform hardware ATA Secure Erase with fallback"""
        try:
            erase_type = "Enhanced " if enhanced else ""
            
            if device_info.is_frozen:
                logger.warning(f"Drive {device_info.name} is in frozen state; power-cycle required for ATA Secure Erase.")
                if progress_callback:
                    progress_callback(10, f"Drive is frozen - falling back to software wipe")
                
                original_method = result['method']
                fallback_method = WipeMethod.DOD_3_PASS
                result['method'] = f"{fallback_method} (Fallback from {original_method})"
                result['compliance'] = get_compliance_info(original_method, is_fallback=True)
                result['compliance']['fallback_method'] = fallback_method
                result['compliance']['original_method'] = original_method
                
                return self._perform_software_wipe(device_info, fallback_method, progress_callback, result)

            if progress_callback:
                progress_callback(10, f"Executing hardware ATA {erase_type}Secure Erase...")

            self._dismount_drive_volumes(device_info.path)

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
                set_pwd_ok = self._send_ata_security_command(handle, self.ATA_SECURITY_SET_PASSWORD, "ZeroTraceErase")
                if not set_pwd_ok:
                    raise Exception("ATA Security Set Password command rejected by controller")

                if progress_callback:
                    progress_callback(30, "Security password set. Issuing ATA Erase Unit...")

                erase_ok = self._send_ata_security_command(
                    handle,
                    self.ATA_SECURITY_ERASE_UNIT,
                    "ZeroTraceErase",
                    enhanced=enhanced
                )
                if not erase_ok:
                    self._send_ata_security_command(handle, self.ATA_SECURITY_DISABLE_PASSWORD, "ZeroTraceErase")
                    raise Exception("ATA Security Erase Unit command failed or timed out")

                if progress_callback:
                    progress_callback(80, "ATA Erase complete. Clearing security password...")

                self._send_ata_security_command(handle, self.ATA_SECURITY_DISABLE_PASSWORD, "ZeroTraceErase")

                win32file.CloseHandle(handle)
                handle = None

                result['passes_completed'] = 1
                result['status'] = 'Completed'
                result['success'] = True
                result['compliance'] = get_compliance_info(result['method'], is_fallback=False)
                
                if progress_callback:
                    progress_callback(90, "Hardware erase completed. Reformatting drive...")

                formatter = DriveFormatter()
                filesystem_info = formatter.detect_original_filesystem(device_info.path)
                formatter.format_drive(device_info.path, filesystem_info, progress_callback)

                return result

            finally:
                if handle:
                    win32file.CloseHandle(handle)

        except Exception as e:
            logger.warning(f"ATA Secure Erase hardware execution failed ({e}). Falling back to software wipe...")
            original_method = result['method']
            fallback_method = WipeMethod.DOD_3_PASS
            result['method'] = f"{fallback_method} (Fallback from {original_method})"
            result['compliance'] = get_compliance_info(original_method, is_fallback=True)
            result['compliance']['fallback_method'] = fallback_method
            result['compliance']['original_method'] = original_method

            return self._perform_software_wipe(device_info, fallback_method, progress_callback, result)

    def _perform_nvme_format(self, device_info: DeviceInfo,
                              progress_callback: Optional[Callable], result: Dict) -> Dict:
        """Perform hardware NVMe Format NVM with software fallback"""
        try:
            if progress_callback:
                progress_callback(10, "Executing hardware NVMe Format NVM...")

            self._dismount_drive_volumes(device_info.path)

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
                # NVMe Format NVM command (Opcode 0x80)
                # CDW10: SES=1 (UserData Erase)
                cdw10 = 0x00000008
                format_ok = self._send_nvme_admin_command(handle, self.NVME_ADMIN_FORMAT_NVM, cdw10=cdw10)

                win32file.CloseHandle(handle)
                handle = None

                if format_ok:
                    result['passes_completed'] = 1
                    result['status'] = 'Completed'
                    result['success'] = True
                    result['compliance'] = get_compliance_info(result['method'], is_fallback=False)

                    if progress_callback:
                        progress_callback(90, "NVMe Format completed. Reformatting drive...")

                    formatter = DriveFormatter()
                    filesystem_info = formatter.detect_original_filesystem(device_info.path)
                    formatter.format_drive(device_info.path, filesystem_info, progress_callback)
                    return result
                else:
                    raise Exception("NVMe Format Admin command returned failure status")

            finally:
                if handle:
                    win32file.CloseHandle(handle)

        except Exception as e:
            logger.warning(f"NVMe Format hardware execution failed ({e}). Falling back to software wipe...")
            original_method = result['method']
            fallback_method = WipeMethod.DOD_3_PASS
            result['method'] = f"{fallback_method} (Fallback from {original_method})"
            result['compliance'] = get_compliance_info(original_method, is_fallback=True)
            result['compliance']['fallback_method'] = fallback_method
            result['compliance']['original_method'] = original_method

            return self._perform_software_wipe(device_info, fallback_method, progress_callback, result)

    def _perform_nvme_sanitize(self, device_info: DeviceInfo, method: str,
                                progress_callback: Optional[Callable], result: Dict) -> Dict:
        """Perform hardware NVMe Sanitize with software fallback"""
        try:
            if progress_callback:
                progress_callback(10, f"Executing hardware {method}...")

            self._dismount_drive_volumes(device_info.path)

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
                # SANACT in CDW10: 2 = Block Erase, 3 = Overwrite, 4 = Crypto Erase
                if method == WipeMethod.NVME_SANITIZE_CRYPTO:
                    cdw10 = 0x00000004
                elif method == WipeMethod.NVME_SANITIZE_BLOCK:
                    cdw10 = 0x00000002
                else:
                    cdw10 = 0x00000003

                sanitize_ok = self._send_nvme_admin_command(handle, self.NVME_ADMIN_SANITIZE, cdw10=cdw10)

                win32file.CloseHandle(handle)
                handle = None

                if sanitize_ok:
                    result['passes_completed'] = 1
                    result['status'] = 'Completed'
                    result['success'] = True
                    result['compliance'] = get_compliance_info(result['method'], is_fallback=False)

                    if progress_callback:
                        progress_callback(90, "NVMe Sanitize completed. Reformatting drive...")

                    formatter = DriveFormatter()
                    filesystem_info = formatter.detect_original_filesystem(device_info.path)
                    formatter.format_drive(device_info.path, filesystem_info, progress_callback)
                    return result
                else:
                    raise Exception("NVMe Sanitize Admin command returned failure status")

            finally:
                if handle:
                    win32file.CloseHandle(handle)

        except Exception as e:
            logger.warning(f"NVMe Sanitize hardware execution failed ({e}). Falling back to software wipe...")
            original_method = result['method']
            fallback_method = WipeMethod.DOD_3_PASS
            result['method'] = f"{fallback_method} (Fallback from {original_method})"
            result['compliance'] = get_compliance_info(original_method, is_fallback=True)
            result['compliance']['fallback_method'] = fallback_method
            result['compliance']['original_method'] = original_method

            return self._perform_software_wipe(device_info, fallback_method, progress_callback, result)

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
                else:
                    passes = [WipePattern.ZEROS, WipePattern.ONES, WipePattern.RANDOM,
                            WipePattern.ZEROS, WipePattern.ONES, WipePattern.RANDOM,
                            WipePattern.ZEROS]

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
                    
                    # Update active wipe journal
                    jnl = self.journal.load_journal()
                    if jnl:
                        self.journal.update_progress(jnl, pass_num, self._current_progress)

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

                    # Close write handle before read-back verification
                    win32file.CloseHandle(handle)
                    handle = None

                    # Open a READ handle for verification sampling
                    try:
                        read_handle = win32file.CreateFile(
                            device_info.path,
                            win32con.GENERIC_READ,
                            win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
                            None,
                            win32con.OPEN_EXISTING,
                            win32con.FILE_FLAG_NO_BUFFERING,
                            None
                        )
                        try:
                            verification = self._generate_verification_hash(
                                read_handle, wipe_size, result['method'],
                                device_info, progress_callback
                            )
                            result['completion_hash'] = verification['hash']
                            result['verification'] = verification
                        finally:
                            win32file.CloseHandle(read_handle)
                    except Exception as ve:
                        logger.warning(f"Read-back verification failed: {ve}")
                        result['completion_hash'] = None
                        result['verification'] = {
                            'hash': None,
                            'verification_method': 'read_back_failed',
                            'error': str(ve)
                        }
                    
                    # Format the drive (96-98% of progress)
                    if progress_callback:
                        progress_callback(96, "Reformatting drive...")
                    
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
            buffer = os.urandom(self._buffer_size)

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
                logger.debug(f"Wipe progress - Pass {pass_num}/{total_passes}, Progress: {self._current_progress}%")

            time.sleep(0.001)

    def _generate_verification_hash(self, handle, drive_size: int, method: str,
                                     device_info: DeviceInfo,
                                     progress_callback: Optional[Callable] = None) -> Dict:
        """Generate SHA-256 hash by reading back sampled blocks post-wipe.

        Reads up to 64 evenly-spaced 1 MB blocks across the drive surface and
        hashes their content together with wipe metadata.  This proves the
        actual state of the disk, not just that a wipe was *requested*.

        Returns:
            Dict with 'hash', 'sample_count', 'sample_size', and
            'verification_method' keys.
        """
        if progress_callback:
            progress_callback(91, "Verifying wipe: reading drive samples...")

        hasher = hashlib.sha256()
        sample_size = self._buffer_size  # 1 MB per sample
        sample_count = min(64, max(1, drive_size // sample_size))
        step = drive_size // sample_count if sample_count > 0 else drive_size
        samples_read = 0

        try:
            for i in range(sample_count):
                offset = i * step
                # Align to sector boundary
                offset = (offset // self._sector_size) * self._sector_size
                read_size = min(sample_size, drive_size - offset)
                if read_size <= 0:
                    break

                win32file.SetFilePointer(handle, offset, win32con.FILE_BEGIN)
                _, data = win32file.ReadFile(handle, read_size)
                hasher.update(data)
                samples_read += 1

                if progress_callback and samples_read % 8 == 0:
                    pct = 91 + int(samples_read / sample_count * 4)  # 91-95%
                    progress_callback(pct, f"Verifying: sampled {samples_read}/{sample_count} blocks")
        except Exception as e:
            logger.warning(f"Read-back verification partially failed at sample {samples_read}: {e}")

        # Include metadata for uniqueness (prevents replaying an old hash)
        hasher.update(f"{device_info.path}:{device_info.serial}:{method}:{datetime.now().isoformat()}".encode())

        return {
            'hash': hasher.hexdigest(),
            'sample_count': samples_read,
            'sample_size': sample_size,
            'verification_method': 'read_back_sampling'
        }

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