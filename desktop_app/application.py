from PyQt5.QtWidgets import QDialog, QApplication, QTextEdit, QVBoxLayout, QPushButton, QHBoxLayout, QLabel, QMessageBox
from PyQt5.QtCore import QSettings
from dialogs import LoginDialog, PinDialog
from pathlib import Path

class EulaDialog(QDialog):
    """EULA Acceptance Dialog"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ZeroTrace — End User License Agreement")
        self.resize(600, 500)
        
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
        decline_btn = QPushButton("Decline")
        accept_btn = QPushButton("Accept & Continue")
        accept_btn.setDefault(True)
        
        decline_btn.clicked.connect(self.reject)
        accept_btn.clicked.connect(self.accept)
        
        btn_layout.addStretch()
        btn_layout.addWidget(decline_btn)
        btn_layout.addWidget(accept_btn)
        layout.addLayout(btn_layout)


class ZeroTraceApplication(QApplication):
    """Main application class with Supabase integration"""
    
    def __init__(self, argv):
        super().__init__(argv)
        self.setApplicationName("ZeroTrace")
        self.setApplicationVersion("1.0")
        self.setOrganizationName("ZeroTrace")
        
        self.main_window = None
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
    
    def authenticate_user(self):
        """Handle user authentication with Supabase"""
        if not self.check_eula_acceptance():
            return False
            
        # Login dialog
        login_dialog = LoginDialog()
        if login_dialog.exec_() != QDialog.Accepted:
            return False
        
        # Get user from login
        self.user = login_dialog.user
        self.supabase_client = login_dialog.supabase
        
        # Check if PIN is required
        user_id = None
        if self.user:
            user_id = self.user.id
            
            # Check if user has PIN set in Supabase
            has_pin = self.check_user_has_pin(user_id)
            
            if has_pin:
                # PIN entry
                pin_dialog = PinDialog(self.supabase_client, user_id, setup_mode=False)
                if pin_dialog.exec_() != QDialog.Accepted:
                    return False
            else:
                # PIN setup
                pin_dialog = PinDialog(self.supabase_client, user_id, setup_mode=True)
                if pin_dialog.exec_() != QDialog.Accepted:
                    return False
        else:
            # Offline mode - use local PIN
            settings = QSettings("ZeroTrace", "Application")
            has_local_pin = settings.value("app_pin_hash", "") or settings.value("app_pin", "")
            
            if has_local_pin:
                pin_dialog = PinDialog(None, None, setup_mode=False)
                if pin_dialog.exec_() != QDialog.Accepted:
                    return False
            else:
                pin_dialog = PinDialog(None, None, setup_mode=True)
                if pin_dialog.exec_() != QDialog.Accepted:
                    return False
        
        return True
    
    def check_user_has_pin(self, user_id: str) -> bool:
        """Check if user has PIN set in Supabase"""
        if not self.supabase_client:
            from logger import logger
            logger.warning("No Supabase client available")
            return False
        
        try:
            from logger import logger
            response = self.supabase_client.table('user_profiles')\
                .select('id, pin_hash')\
                .eq('id', user_id)\
                .execute()
            
            if response.data and len(response.data) > 0:
                pin_hash = response.data[0].get('pin_hash')
                has_pin = bool(pin_hash)
                logger.info(f"User {user_id} has PIN configured: {has_pin}")
                return has_pin
            else:
                logger.info(f"No profile found for user {user_id}")
                return False
                
        except Exception as e:
            from logger import logger
            logger.error(f"Error checking PIN for {user_id}: {e}", exc_info=True)
            return False
    
    def run(self):
        """Run the application"""
        if not self.authenticate_user():
            return 1
        
        # Create main window and pass both client and user
        from main_window import ZeroTraceMainWindow
        self.main_window = ZeroTraceMainWindow(
            supabase_client=self.supabase_client,
            user=self.user  # Pass the authenticated user
        )
        self.main_window.show()
        
        return self.exec_()