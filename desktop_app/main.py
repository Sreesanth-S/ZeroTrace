#!/usr/bin/env python3
"""
ZeroTrace Complete Desktop Application
A fully functional device wiping and certification application

Requirements:
    pip install PyQt5 pycryptodome reportlab qrcode[pil] pillow

Usage:
    python3 zerotrace_app.py
"""
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
    for directory in ["logs", "keys", "certificates"]:
        Path(directory).mkdir(exist_ok=True)
    
    # Check for required dependencies
    try:
        import PyQt5
        from Crypto.PublicKey import ECC
        from reportlab.pdfgen import canvas
        import qrcode
    except ImportError as e:
        print(f"Missing required dependency: {e}")
        print("\nPlease install required packages:")
        print("pip install PyQt5 pycryptodome reportlab qrcode[pil] pillow")
        return 1
    
    # Create and run application
    app = ZeroTraceApplication(sys.argv)
    return app.run()

if __name__ == "__main__":
    sys.exit(main())