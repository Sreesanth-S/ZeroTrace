import os
import win32api
import win32file
import win32con
import winioctlcon
import random
import time
import logging
import subprocess
import psutil
import struct
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
    
    def _get_physical_drive_number(self, drive_letter):
        """Convert drive letter to physical drive number using psutil"""
        try:
            drive_letter = drive_letter.replace(':', '').upper()
            print(f"[INFO] Looking for physical drive number for drive {drive_letter}")
            
            # Use PowerShell WMI query (most reliable method)
            ps_script = f"""
$drive = Get-WmiObject -Class Win32_LogicalDisk -Filter "DeviceID='{drive_letter}:'"
if ($drive) {{
    $partitions = Get-WmiObject -Class Win32_LogicalDiskToPartition | Where-Object {{ $_.Dependent -like "*$($drive.DeviceID)*" }}
    foreach ($partition in $partitions) {{
        $antecedent = $partition.Antecedent
        $diskMatch = [regex]::Match($antecedent, 'Disk #(\\d+)')
        if ($diskMatch.Success) {{
            Write-Output $diskMatch.Groups[1].Value
            break
        }}
    }}
}}
"""
            result = subprocess.run(
                ['powershell', '-Command', ps_script],
                capture_output=True, 
                text=True,
                timeout=15
            )
            
            if result.returncode == 0 and result.stdout.strip():
                disk_num = int(result.stdout.strip())
                print(f"[SUCCESS] Found disk number {disk_num} via PowerShell WMI")
                return disk_num
            
            raise Exception(f"Could not find physical drive number for {drive_letter}")
            
        except Exception as e:
            raise Exception(f"Error finding physical drive number: {e}")
    
    def get_physical_drives_list(self):
        """Get list of all physical drives with their numbers and sizes"""
        drives = []
        for i in range(10):  # Check first 10 drives
            try:
                path = f"\\\\.\\PhysicalDrive{i}"
                handle = win32file.CreateFile(
                    path,
                    win32con.GENERIC_READ,
                    win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
                    None,
                    win32con.OPEN_EXISTING,
                    0,
                    None
                )
                if handle != win32file.INVALID_HANDLE_VALUE:
                    try:
                        # Use DeviceIoControl to get drive size
                        drive_size = self._get_drive_size(handle)
                        if drive_size > 0:
                            drives.append({
                                'number': i,
                                'size_gb': drive_size / (1024**3),
                                'path': path
                            })
                            print(f"[INFO] Found PhysicalDrive{i}: {drive_size / (1024**3):.2f} GB")
                    except Exception as e:
                        print(f"[INFO] PhysicalDrive{i} size unavailable: {e}")
                    finally:
                        win32file.CloseHandle(handle)
            except Exception as e:
                # This is normal for drives that don't exist
                continue
        return drives

    def _get_drive_size(self, drive_handle):
        """Get drive size using DeviceIoControl with IOCTL_DISK_GET_LENGTH_INFO"""
        try:
            # Method 1: IOCTL_DISK_GET_LENGTH_INFO (most reliable)
            output = win32file.DeviceIoControl(
                drive_handle,
                winioctlcon.IOCTL_DISK_GET_LENGTH_INFO,
                None,
                8  # sizeof(LARGE_INTEGER)
            )
            # Unpack the 64-bit integer
            drive_size = struct.unpack('Q', output)[0]
            return drive_size
        except:
            try:
                # Method 2: IOCTL_DISK_GET_DRIVE_GEOMETRY_EX
                output = win32file.DeviceIoControl(
                    drive_handle,
                    winioctlcon.IOCTL_DISK_GET_DRIVE_GEOMETRY_EX,
                    None,
                    1024  # Reasonable buffer size
                )
                # The first 8 bytes are the drive size
                drive_size = struct.unpack('Q', output[:8])[0]
                return drive_size
            except:
                try:
                    # Method 3: Get disk geometry (older method)
                    output = win32file.DeviceIoControl(
                        drive_handle,
                        winioctlcon.IOCTL_DISK_GET_DRIVE_GEOMETRY,
                        None,
                        24  # sizeof(DISK_GEOMETRY)
                    )
                    # Structure: LARGE_INTEGER Cylinders, MEDIA_TYPE MediaType, DWORD TracksPerCylinder, 
                    # DWORD SectorsPerTrack, DWORD BytesPerSector
                    cylinders, media_type, tracks_per_cylinder, sectors_per_track, bytes_per_sector = struct.unpack('QIIII', output)
                    drive_size = cylinders * tracks_per_cylinder * sectors_per_track * bytes_per_sector
                    return drive_size
                except Exception as e:
                    print(f"[WARN] All drive size methods failed: {e}")
                    return 0

    def _cleanup_disk_handles(self, physical_drive_number):
        """Force cleanup of any handles to the disk"""
        print(f"[INFO] Cleaning up handles for PhysicalDrive{physical_drive_number}...")
        
        try:
            # Use handle.exe from Sysinternals to close any open handles
            handle_paths = [
                "handle.exe",
                "handle64.exe", 
                r"C:\Tools\handle.exe",
                r"C:\Tools\handle64.exe"
            ]
            
            handle_exe = None
            for path in handle_paths:
                try:
                    subprocess.run([path, "-?"], capture_output=True, timeout=5)
                    handle_exe = path
                    break
                except:
                    continue
            
            if handle_exe:
                cmd = [handle_exe, "-p", "System", "-c", f"*PhysicalDrive{physical_drive_number}", "-y"]
                subprocess.run(cmd, capture_output=True, timeout=10)
                print("[INFO] Used handle.exe to close existing handles")
        except Exception as e:
            print(f"[INFO] Handle cleanup not available: {e}")

    def _force_dismount(self, physical_drive_number):
        """Force dismount using multiple methods"""
        print(f"[INFO] Force dismounting PhysicalDrive{physical_drive_number}...")
        
        # Method 1: Use diskpart to clean the disk
        try:
            diskpart_script = f"""
select disk {physical_drive_number}
offline disk
online disk
attributes disk clear readonly
clean
rescan
exit
"""
            result = subprocess.run(
                ['diskpart'], 
                input=diskpart_script, 
                capture_output=True, 
                text=True,
                timeout=30
            )
            print(f"[INFO] Diskpart clean completed with return code: {result.returncode}")
        except Exception as e:
            print(f"[WARN] Diskpart clean failed: {e}")

        # Method 2: Use PowerShell to remove disk
        try:
            ps_script = f"""
$disk = Get-Disk -Number {physical_drive_number}
if ($disk) {{
    Set-Disk -Number {physical_drive_number} -IsOffline $true
    Start-Sleep -Seconds 2
    Set-Disk -Number {physical_drive_number} -IsOffline $false
    Start-Sleep -Seconds 2
}}
"""
            subprocess.run(
                ['powershell', '-Command', ps_script],
                capture_output=True, 
                timeout=20
            )
            print("[INFO] PowerShell disk offline/online completed")
        except Exception as e:
            print(f"[INFO] PowerShell method failed: {e}")

    def start_wipe(self, drive_identifier, progress_callback=None):
        """Perform full physical drive wipe"""
        
        try:
            # Show available physical drives for debugging
            print("[INFO] Available physical drives:")
            physical_drives = self.get_physical_drives_list()
            for drive in physical_drives:
                print(f"  - PhysicalDrive{drive['number']}: {drive['size_gb']:.2f} GB")

            # Determine if we have a drive letter or physical drive number
            if isinstance(drive_identifier, str) and drive_identifier.replace(':', '').isalpha():
                # It's a drive letter, convert to physical drive number
                print(f"[INFO] Converting drive letter {drive_identifier} to physical drive number...")
                physical_drive_number = self._get_physical_drive_number(drive_identifier)
                print(f"[SUCCESS] Drive {drive_identifier} maps to PhysicalDrive{physical_drive_number}")
            else:
                # Assume it's already a physical drive number
                physical_drive_number = drive_identifier

            print(f"[INFO] Preparing full wipe on PhysicalDrive{physical_drive_number}...")
            
            # Force dismount using multiple methods
            self._force_dismount(physical_drive_number)
            
            # Clean up any remaining handles
            self._cleanup_disk_handles(physical_drive_number)
            
            # Give system ample time to release all handles
            print("[INFO] Waiting for system to release handles...")
            for i in range(5, 0, -1):
                print(f"[INFO] Waiting {i} seconds...")
                time.sleep(1)

            # Open physical drive with retry logic
            drive_path = f"\\\\.\\PhysicalDrive{physical_drive_number}"
            print(f"[INFO] Opening drive: {drive_path}")
            
            drive_handle = None
            for attempt in range(5):
                try:
                    drive_handle = win32file.CreateFile(
                        drive_path,
                        win32con.GENERIC_READ | win32con.GENERIC_WRITE,
                        0,  # No sharing - exclusive access
                        None,
                        win32con.OPEN_EXISTING,
                        win32con.FILE_FLAG_NO_BUFFERING | win32con.FILE_FLAG_WRITE_THROUGH,
                        None
                    )
                    
                    if drive_handle != win32file.INVALID_HANDLE_VALUE:
                        print(f"[SUCCESS] Got exclusive access on attempt {attempt + 1}")
                        break
                    else:
                        print(f"[INFO] Attempt {attempt + 1} failed, retrying...")
                        time.sleep(2)
                        
                except Exception as e:
                    print(f"[INFO] Attempt {attempt + 1} failed: {e}")
                    if attempt < 4:  # Don't sleep on last attempt
                        time.sleep(2)
            
            if not drive_handle or drive_handle == win32file.INVALID_HANDLE_VALUE:
                error_code = win32api.GetLastError()
                raise Exception(f"Failed to open physical drive after 5 attempts. Error code: {error_code}")
            
            print(f"[SUCCESS] Got exclusive access to PhysicalDrive{physical_drive_number}")

            try:
                # Get drive size using DeviceIoControl
                drive_size = self._get_drive_size(drive_handle)
                if drive_size == 0:
                    raise Exception("Could not determine drive size")
                
                print(f"[INFO] Drive size: {drive_size} bytes ({drive_size / (1024**3):.2f} GB)")

                # Prepare buffer for writing
                buffer_size = 1024 * 1024  # 1MB
                print(f"[INFO] Starting wipe process...")

                written = 0
                start_time = time.time()
                
                while written < drive_size and not self._stop_requested:
                    # Calculate how much to write in this iteration
                    remaining = drive_size - written
                    current_buffer_size = min(buffer_size, remaining)
                    
                    # Generate random data for secure wipe
                    write_buffer = os.urandom(current_buffer_size)
                    
                    # Write to drive
                    try:
                        win32file.WriteFile(drive_handle, write_buffer)
                        written += len(write_buffer)
                    except Exception as write_error:
                        print(f"[WARN] Write error at position {written}: {write_error}")
                        # Try to continue from current position
                        continue
                    
                    # Update progress
                    if progress_callback:
                        progress = int((written / drive_size) * 100)
                        elapsed_time = time.time() - start_time
                        if written > 0 and elapsed_time > 0:
                            speed_mbps = (written / (1024 * 1024)) / elapsed_time
                            status = f"Wiping... {speed_mbps:.1f} MB/s"
                        else:
                            status = "Wiping..."
                        progress_callback(progress, status)
                    
                    # Print progress every 5%
                    if written % (drive_size // 20) < buffer_size or written == drive_size:
                        percent_complete = (written / drive_size) * 100
                        elapsed = time.time() - start_time
                        speed = (written / (1024 * 1024)) / elapsed if elapsed > 0 else 0
                        print(f"[INFO] Progress: {percent_complete:.1f}% - {speed:.1f} MB/s")
                
                if self._stop_requested:
                    print("[INFO] Wipe operation stopped by user")
                    return False
                else:
                    total_time = time.time() - start_time
                    avg_speed = (drive_size / (1024 * 1024)) / total_time if total_time > 0 else 0
                    print(f"[SUCCESS] Full wipe completed in {total_time:.1f}s ({avg_speed:.1f} MB/s)")
                    return True
                    
            finally:
                if drive_handle:
                    win32file.CloseHandle(drive_handle)
                    print("[INFO] Drive handle closed")

        except Exception as e:
            print(f"Error during wipe: {e}")
            import traceback
            traceback.print_exc()
            return False

    def stop_wipe(self):
        """Stop the wiping process"""
        self._stop_requested = True
        print("[INFO] Stop requested")
    
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
        safe_device = device.replace(':', '').replace('\\', '').replace('/', '')
        log_filename = f"wipe_log_{safe_device}_{timestamp}.txt"
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

            # Reset stop flag for new operation
            self._stop_requested = False

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