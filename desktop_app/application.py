from PyQt5.QtWidgets import QDialog, QApplication,QMessageBox 
from PyQt5.QtCore import QSettings
from dialogs import LoginDialog, PinDialog
from main_window import ZeroTraceMainWindow

class ZeroTraceApplication(QApplication):
    """Main application class"""
    
    def __init__(self, argv):
        super().__init__(argv)
        self.setApplicationName("ZeroTrace")
        self.setApplicationVersion("1.0")
        self.setOrganizationName("ZeroTrace")
        
        # Set application icon (if available)
        # self.setWindowIcon(QIcon("icon.png"))
        
        self.main_window = None
    
    def authenticate_user(self):
        """Handle user authentication"""
        # Login dialog
        login_dialog = LoginDialog()
        if login_dialog.exec_() != QDialog.Accepted:
            return False
        
        # PIN setup/entry
        settings = QSettings("ZeroTrace", "Application")
        stored_pin = settings.value("app_pin", "")
        
        if stored_pin:
            # PIN entry
            pin_dialog = PinDialog(setup_mode=False)
            if pin_dialog.exec_() != QDialog.Accepted:
                return False
            
            # Verify PIN (in real app, this would be properly hashed)
            if pin_dialog.pin != stored_pin:
                QMessageBox.critical(None, "Authentication Failed", "Incorrect PIN")
                return False
        else:
            # PIN setup
            pin_dialog = PinDialog(setup_mode=True)
            if pin_dialog.exec_() != QDialog.Accepted:
                return False
            
            # Save PIN (in real app, this would be properly hashed and secured)
            settings.setValue("app_pin", pin_dialog.pin)
        
        return True
    
    def run(self):
        """Run the application"""
        # Authenticate user
        if not self.authenticate_user():
            return 1
        
        # Create and show main window
        self.main_window = ZeroTraceMainWindow()
        self.main_window.show()
        
        return self.exec_()