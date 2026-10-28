import sys, ctypes, logging
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
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

def ensure_runtime_log_console():
    """
    Ensure an interactive log console window/tab opens behind the desktop application
    strictly during development runs. In the compiled executable, no console window is spawned.
    """
    if getattr(sys, 'frozen', False):
        return

    if sys.platform == "win32":
        try:
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if not hwnd:
                ctypes.windll.kernel32.AllocConsole()
                sys.stdout = open("CONOUT$", "w", buffering=1, encoding="utf-8")
                sys.stderr = open("CONOUT$", "w", buffering=1, encoding="utf-8")
                hwnd = ctypes.windll.kernel32.GetConsoleWindow()

            if hwnd:
                ctypes.windll.kernel32.SetConsoleTitleW("ZeroTrace — Live Runtime Log Console")
                # Show console window behind main window without stealing focus (SW_SHOWNOACTIVATE = 4)
                ctypes.windll.user32.ShowWindow(hwnd, 4)
        except Exception:
            pass

def main():
    """Main entry point"""
    is_frozen = getattr(sys, 'frozen', False)

    if is_frozen:
        # In compiled executable: suppress console window and stream
        logging.basicConfig(level=logging.INFO, handlers=[logging.NullHandler()])
    else:
        # In development: open live log console tab behind the application during run time
        ensure_runtime_log_console()
        logging.basicConfig(
            level=logging.DEBUG,
            format='[%(asctime)s] [%(levelname)s] %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            stream=sys.stdout
        )

    # Enable High-DPI scaling and pixmaps to prevent text lag and clipping
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # Create and run application
    app = ZeroTraceApplication(sys.argv)
    return app.run()

if __name__ == "__main__":
    sys.exit(main())
