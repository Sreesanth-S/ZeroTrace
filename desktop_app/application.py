import sys
import ctypes
from pathlib import Path
from PyQt5.QtWidgets import QDialog, QApplication, QTextEdit, QVBoxLayout, QPushButton, QHBoxLayout, QLabel, QMessageBox
from PyQt5.QtCore import QSettings
from PyQt5.QtGui import QIcon
from dialogs import LoginDialog

ASSETS_DIR = Path(__file__).parent / "assets"
APP_ICON_PATH = (ASSETS_DIR / "ZeroTrace.png").resolve()

class EulaDialog(QDialog):
    """EULA Acceptance Dialog"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ZeroTrace — End User License Agreement")
        if APP_ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(APP_ICON_PATH)))
        self.resize(600, 500)
        from dialogs import DIALOG_STYLESHEET
        self.setStyleSheet(DIALOG_STYLESHEET)
        
        layout = QVBoxLayout(self)
        
        label = QLabel("Please review and accept the End User License Agreement before using ZeroTrace:")
        label.setWordWrap(True)
        layout.addWidget(label)
        
        text_edit = QTextEdit(self)
        text_edit.setReadOnly(True)
        
        eula_path = Path(__file__).parent / "EULA.txt"
        if eula_path.exists():
            text_edit.setText(eula_path.read_text(encoding="utf-8"))
        else:
            text_edit.setText("EULA file not found.")
            
        layout.addWidget(text_edit)
        
        btn_layout = QHBoxLayout()
        self.decline_btn = QPushButton("Decline")
        self.accept_btn = QPushButton("Accept & Continue")
        self.accept_btn.setDefault(True)
        
        self.decline_btn.clicked.connect(self.reject)
        self.accept_btn.clicked.connect(self.on_accept_clicked)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.decline_btn)
        btn_layout.addWidget(self.accept_btn)
        layout.addLayout(btn_layout)

    def on_accept_clicked(self):
        self.accept_btn.setEnabled(False)
        self.decline_btn.setEnabled(False)
        self.accept_btn.setText("Loading...")
        QApplication.processEvents()
        self.accept()


class ZeroTraceApplication(QApplication):
    """Main application class with FastAPI backend integration"""
    
    def __init__(self, argv):
        super().__init__(argv)
        self.setApplicationName("ZeroTrace")
        self.setApplicationVersion("1.0")
        self.setOrganizationName("ZeroTrace")

        # Explicit AppUserModelID ensures Windows taskbar binds to custom app icon
        if sys.platform == "win32":
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("zerotrace.desktop.app")
            except Exception:
                pass

        if APP_ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(APP_ICON_PATH)))
        
        # Apply authoritative modern single stylesheet globally
        from main_window import MODERN_STYLESHEET
        self.setStyleSheet(MODERN_STYLESHEET)
        
        self.main_window = None
        self.backend_client = None
        self.supabase_client = None
        self.user = None
    
    def check_eula_acceptance(self) -> bool:
        settings = QSettings("ZeroTrace", "Application")
        if settings.value("eula_accepted", False, type=bool):
            return True
            
        dialog = EulaDialog()
        if dialog.exec_() == QDialog.Accepted:
            settings.setValue("eula_accepted", True)
            return True
        return False
    
    def ensure_internet_connection(self) -> bool:
        """
        Mandate an active internet connection before allowing login.
        Repeatedly prompts the user if no connection is detected.
        """
        from backend_client import check_internet_connection

        while not check_internet_connection():
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("⚠️ Internet Connection Required")
            msg_box.setText("ZeroTrace mandates an active internet connection before login.")
            msg_box.setInformativeText(
                "An active internet connection is strictly required to verify identity, "
                "authenticate credentials, and ensure cloud-authoritative audit logging.\n\n"
                "Please connect to the internet and click 'Retry Connection'."
            )
            retry_btn = msg_box.addButton("Retry Connection", QMessageBox.ActionRole)
            exit_btn = msg_box.addButton("Exit Application", QMessageBox.RejectRole)
            msg_box.setDefaultButton(retry_btn)
            msg_box.exec_()

            if msg_box.clickedButton() == exit_btn:
                return False

        return True

    def authenticate_user(self):
        """Handle user authentication with FastAPI backend"""
        # Mandate internet connectivity before proceeding to login
        if not self.ensure_internet_connection():
            return False

        if not self.check_eula_acceptance():
            return False

        from backend_client import backend_client, UserProxy

        # Restore persisted login session (browser-like behavior on Exit)
        if backend_client.session and backend_client.ensure_valid_session() and backend_client.user:
            self.backend_client = backend_client
            self.supabase_client = backend_client
            self.session = backend_client.session
            self.user = UserProxy(backend_client.user)
            return True
            
        # Login dialog
        login_dialog = LoginDialog()
        if login_dialog.exec_() != QDialog.Accepted:
            return False
        
        # Get user from login
        self.user = login_dialog.user
        self.session = login_dialog.session
        self.backend_client = getattr(login_dialog, "backend", getattr(login_dialog, "supabase", None))
        self.supabase_client = self.backend_client
        
        if not self.user or not self.backend_client:
            return False
        
        return True
    
    def run(self):
        """Run the application lifecycle"""
        from main_window import ZeroTraceMainWindow

        while True:
            if not self.authenticate_user():
                return 0

            # Create main window and pass client, user, and session
            self.main_window = ZeroTraceMainWindow(
                backend_client_instance=self.backend_client,
                user=self.user,
                session=self.session
            )
            self.main_window.show()

            self.exec_()

            # If user explicitly logged out, return to login dialog
            if getattr(self.main_window, 'logged_out', False):
                self.user = None
                self.session = None
                self.main_window = None
                continue
            else:
                # User clicked Exit or closed the window (session is persisted)
                break

        return 0