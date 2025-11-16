from PyQt5.QtWidgets import QDialog, QApplication,QMessageBox 
from PyQt5.QtCore import QSettings
from dialogs import LoginDialog, PinDialog
from main_window import ZeroTraceMainWindow
from certificate_manager import CertificateManager
from logger import logger

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
    
    def authenticate_user(self):
        """Handle user authentication with Supabase"""
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
            print("No Supabase client available")
            return False
        
        try:
            response = self.supabase_client.table('user_profiles')\
                .select('id, pin_hash')\
                .eq('id', user_id)\
                .execute()
            
            print(f"Check PIN response for {user_id}: {response.data}")
            
            if response.data and len(response.data) > 0:
                pin_hash = response.data[0].get('pin_hash')
                has_pin = bool(pin_hash)
                print(f"User has PIN: {has_pin} (hash present: {pin_hash is not None})")
                return has_pin
            else:
                print(f"No profile found for user {user_id}")
                return False
                
        except Exception as e:
            print(f"Error checking PIN: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run(self):
        """Run the application"""
        if not self.authenticate_user():
            return 1
        
        # Create main window
        from main_window import ZeroTraceMainWindow
        self.main_window = ZeroTraceMainWindow(supabase_client=self.supabase_client)
        self.main_window.show()
        
        return self.exec_()