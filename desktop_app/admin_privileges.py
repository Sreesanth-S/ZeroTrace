# desktop_app/admin_privileges.py
"""
Administrator privileges management for Windows
Handles UAC elevation and verification
"""

import sys
import os
import ctypes
from typing import Tuple

def is_admin() -> bool:
    """
    Check if the application is running with administrator privileges
    
    Returns:
        bool: True if running as admin, False otherwise
    """
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False


def request_admin_elevation() -> bool:
    """
    Request administrator elevation by relaunching the application
    
    Returns:
        bool: True if elevation was attempted, False if failed
    """
    try:
        # Get the path to the current executable or script
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            script = sys.executable
        else:
            # Running as Python script
            script = os.path.abspath(sys.argv[0])
        
        # Parameters to pass to the elevated process
        params = ' '.join([f'"{arg}"' for arg in sys.argv[1:]])
        
        # Request elevation using ShellExecute with 'runas' verb
        result = ctypes.windll.shell32.ShellExecuteW(
            None,           # Parent window
            "runas",        # Verb (runas = run as administrator)
            sys.executable if getattr(sys, 'frozen', False) else sys.executable,
            f'"{script}" {params}',  # Parameters
            None,           # Working directory
            1               # Show window (SW_SHOWNORMAL)
        )
        
        # If result > 32, elevation was initiated successfully
        if result > 32:
            return True
        else:
            return False
            
    except Exception as e:
        print(f"Failed to request elevation: {e}")
        return False


def check_and_elevate() -> Tuple[bool, str]:
    """
    Check if running as admin, if not, request elevation
    
    Returns:
        Tuple[bool, str]: (is_admin, message)
    """
    if is_admin():
        return True, "Running with administrator privileges"
    
    # Not admin, try to elevate
    print("Application requires administrator privileges.")
    print("Requesting elevation...")
    
    if request_admin_elevation():
        # Elevation requested successfully, exit current instance
        sys.exit(0)
    else:
        # Elevation failed or was denied
        return False, "Administrator privileges required but could not be obtained"


def verify_admin_or_exit():
    """
    Verify admin privileges or exit the application
    Should be called at application startup
    """
    if not is_admin():
        print("ERROR: This application requires administrator privileges.")
        print("Please run as administrator.")
        
        # Try to elevate
        if request_admin_elevation():
            # Exit current instance as elevated one will start
            sys.exit(0)
        else:
            # Could not elevate, exit with error
            print("\nFailed to obtain administrator privileges.")
            print("Please right-click the application and select 'Run as administrator'.")
            sys.exit(1)


def get_elevation_status() -> dict:
    """
    Get detailed elevation status information
    
    Returns:
        dict: Status information
    """
    admin = is_admin()
    
    return {
        'is_admin': admin,
        'elevation_available': sys.platform == 'win32',
        'can_request_elevation': sys.platform == 'win32' and not admin,
        'status_message': 'Administrator' if admin else 'Standard User',
        'requires_elevation': not admin
    }


if __name__ == "__main__":
    # Test the module
    status = get_elevation_status()
    print("Elevation Status:")
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    if not status['is_admin']:
        print("\nAttempting to elevate...")
        check_and_elevate()