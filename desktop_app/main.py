#!/usr/bin/env python3
import sys, ctypes
from pathlib import Path
from application import ZeroTraceApplication

def ensure_admin():
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    except:
        is_admin = False

    if not is_admin:
        # Relaunch with admin rights
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit(0)

ensure_admin()

def main():
    """Main entry point"""
    # Create required directories
    Path("certificates").mkdir(exist_ok=True)
    
    # Create and run application
    app = ZeroTraceApplication(sys.argv)
    return app.run()

if __name__ == "__main__":
    sys.exit(main())