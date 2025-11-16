from PyQt5.QtWidgets import QDialog, QApplication,QMessageBox 
from PyQt5.QtCore import QSettings
from dialogs import LoginDialog, PinDialog
from main_window import ZeroTraceMainWindow
from certificate_manager import CertificateManager
from logger import logger

class ZeroTraceApplication(QApplication):
    """Main application class"""
    
    def __init__(self, argv):
        super().__init__(argv)
        self.setApplicationName("ZeroTrace")
        self.setApplicationVersion("1.0")
        self.setOrganizationName("ZeroTrace")
        self.main_window = None
        self.supabase_client = None
    
    def authenticate_user(self):
        """Handle user authentication"""
        # Login dialog
        login_dialog = LoginDialog()
        if login_dialog.exec_() != QDialog.Accepted:
            return False
        
        # Initialize Supabase client (optional - can work offline)
        try:
            from supabase_client import SupabaseDesktopClient
            self.supabase_client = SupabaseDesktopClient()
            
            # Try to sign in with credentials
            username = login_dialog.username_edit.text()
            password = login_dialog.password_edit.text()
            
            # Attempt Supabase login (non-blocking)
            try:
                self.supabase_client.sign_in(username, password)
                logger.info(f"Logged in to Supabase: {username}")
            except:
                logger.warning("Supabase login failed - continuing in offline mode")
                
        except Exception as e:
            logger.warning(f"Supabase not available: {e} - continuing in offline mode")
            self.supabase_client = None
        
        # PIN setup/entry (existing code)
        settings = QSettings("ZeroTrace", "Application")
        stored_pin = settings.value("app_pin", "")
        
        if stored_pin:
            pin_dialog = PinDialog(setup_mode=False)
            if pin_dialog.exec_() != QDialog.Accepted:
                return False
            
            if pin_dialog.pin != stored_pin:
                QMessageBox.critical(None, "Authentication Failed", "Incorrect PIN")
                return False
        else:
            pin_dialog = PinDialog(setup_mode=True)
            if pin_dialog.exec_() != QDialog.Accepted:
                return False
            
            settings.setValue("app_pin", pin_dialog.pin)
        
        return True
    
    def run(self):
        """Run the application"""
        if not self.authenticate_user():
            return 1
        
        # Create main window and pass Supabase client
        self.main_window = ZeroTraceMainWindow(supabase_client=self.supabase_client)
        self.main_window.show()
        
        return self.exec_()