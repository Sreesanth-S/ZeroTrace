import win32api
import win32file
import win32con
import string

def get_removable_drives():
    """Get a list of removable drives"""
    drives = []
    
    # Get list of drive letters
    drive_letters = list(string.ascii_uppercase)
    
    for letter in drive_letters:
        drive = f"{letter}:"
        try:
            drive_type = win32file.GetDriveType(drive)
            
            # Check if drive is removable
            if drive_type == win32file.DRIVE_REMOVABLE:
                # Try to get drive info to verify it's accessible
                volume_info = win32api.GetVolumeInformation(drive + "\\")
                drives.append(drive)
                
        except:
            # Skip drives that can't be accessed
            continue
    
    return drives
