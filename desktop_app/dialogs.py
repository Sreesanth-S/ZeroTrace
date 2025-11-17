from PyQt5.QtWidgets import (QDialog, QLabel, QVBoxLayout, QLineEdit, QMessageBox, 
                             QDialogButtonBox, QGroupBox, QStyle, QPushButton, QCheckBox)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QFont
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import bcrypt

load_dotenv()

class LoginDialog(QDialog):
    """Login dialog with Supabase authentication"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ZeroTrace Login")
        self.setFixedSize(400, 550)
        self.settings = QSettings("ZeroTrace", "Application")
        
        # Initialize Supabase client
        try:
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_KEY')
            supabase_service_key = os.getenv('SUPABASE_SERVICE_KEY')
            
            if supabase_url and supabase_service_key:
                self.supabase = create_client(supabase_url, supabase_service_key)
                self.supabase_available = True
            else:
                self.supabase = None
                self.supabase_available = False
                print("Warning: Supabase credentials not found. Running in offline mode.")
        except Exception as e:
            self.supabase = None
            self.supabase_available = False
            print(f"Warning: Supabase initialization failed: {e}")
        
        self.user = None
        self.session = None
        
        # Set dialog style (same as before)
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2c3e50, stop:1 #3498db);
            }
            QGroupBox {
                background-color: rgba(255, 255, 255, 220);
                border-radius: 10px;
                margin-top: 1em;
                padding: 15px;
            }
            QLabel {
                color: white;
                font-size: 12px;
            }
            QLineEdit {
                padding: 8px;
                border: 2px solid #3498db;
                border-radius: 5px;
                background-color: white;
                font-size: 12px;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
                min-width: 100px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QCheckBox {
                color: white;
                font-size: 11px;
            }
            QDialogButtonBox {
                button-layout: center;
            }
        """)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Logo/Title section
        icon_label = QLabel()
        icon_label.setPixmap(self.style().standardIcon(QStyle.SP_VistaShield).pixmap(64, 64))
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)
        
        title = QLabel("ZeroTrace")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Segoe UI", 24, QFont.Bold))
        layout.addWidget(title)
        
        subtitle = QLabel("Secure Device Wiping & Certification")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setFont(QFont("Segoe UI", 12))
        layout.addWidget(subtitle)
        
        # Connection status
        if self.supabase_available:
            status_label = QLabel("✓ Connected to Cloud")
            status_label.setStyleSheet("color: #2ecc71; font-weight: bold;")
        else:
            status_label = QLabel("⚠ Offline Mode")
            status_label.setStyleSheet("color: #f39c12; font-weight: bold;")
        status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(status_label)
        
        layout.addSpacing(10)
        
        # Create login group box
        login_group = QGroupBox("Login Details")
        login_group.setFont(QFont("Segoe UI", 10, QFont.Bold))
        login_layout = QVBoxLayout(login_group)
        login_layout.setSpacing(10)
        
        # Email field
        email_label = QLabel("Email:")
        email_label.setFont(QFont("Segoe UI", 10))
        email_label.setStyleSheet("color: #2c3e50;")
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("Enter your email")
        self.email_edit.setFont(QFont("Segoe UI", 10))
        login_layout.addWidget(email_label)
        login_layout.addWidget(self.email_edit)
        
        # Password field
        password_label = QLabel("Password:")
        password_label.setFont(QFont("Segoe UI", 10))
        password_label.setStyleSheet("color: #2c3e50;")
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Enter your password")
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setFont(QFont("Segoe UI", 10))
        login_layout.addWidget(password_label)
        login_layout.addWidget(self.password_edit)
        
        # Remember me checkbox
        self.remember_me = QCheckBox("Remember email")
        self.remember_me.setStyleSheet("color: #2c3e50;")
        login_layout.addWidget(self.remember_me)
        
        layout.addWidget(login_group)
        
        layout.addSpacing(10)
        
        # Buttons
        button_box = QDialogButtonBox()
        
        login_btn = QPushButton("Login")
        login_btn.setFont(QFont("Segoe UI", 10, QFont.Bold))
        login_btn.clicked.connect(self.authenticate)
        
        signup_btn = QPushButton("Sign Up")
        signup_btn.setFont(QFont("Segoe UI", 10))
        signup_btn.clicked.connect(self.show_signup)
        
        offline_btn = QPushButton("Continue Offline")
        offline_btn.setFont(QFont("Segoe UI", 10))
        offline_btn.clicked.connect(self.continue_offline)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFont(QFont("Segoe UI", 10))
        cancel_btn.clicked.connect(self.reject)
        
        button_box.addButton(login_btn, QDialogButtonBox.AcceptRole)
        button_box.addButton(signup_btn, QDialogButtonBox.ActionRole)
        button_box.addButton(offline_btn, QDialogButtonBox.ActionRole)
        button_box.addButton(cancel_btn, QDialogButtonBox.RejectRole)
        
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        
        # Load saved email
        saved_email = self.settings.value("email", "")
        if saved_email:
            self.email_edit.setText(saved_email)
            self.remember_me.setChecked(True)
            self.password_edit.setFocus()
        else:
            self.email_edit.setFocus()
    
    def authenticate(self):
        """Authenticate user with Supabase"""
        email = self.email_edit.text().strip()
        password = self.password_edit.text()
        
        if not email or not password:
            QMessageBox.warning(self, "Error", "Please enter both email and password")
            return
        
        if '@' not in email:
            QMessageBox.warning(self, "Error", "Please enter a valid email address")
            return
        
        if not self.supabase_available:
            QMessageBox.warning(
                self, 
                "Offline Mode", 
                "Supabase is not available.\n\nClick 'Continue Offline' to use the app without cloud features."
            )
            return
        
        try:
            # Sign in with Supabase
            response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if response.user and response.session:
                self.user = response.user
                self.session = response.session
                
                # IMPORTANT: Set the session on the client for RLS
                self.supabase.auth.set_session(response.session.access_token, response.session.refresh_token)
                
                # Save email if remember me is checked
                if self.remember_me.isChecked():
                    self.settings.setValue("email", email)
                else:
                    self.settings.remove("email")
                
                QMessageBox.information(
                    self,
                    "Login Successful",
                    f"Welcome back, {email}!"
                )
                self.accept()
            else:
                QMessageBox.critical(
                    self,
                    "Authentication Failed",
                    "Invalid email or password"
                )
                
        except Exception as e:
            error_msg = str(e)
            
            if "Invalid login credentials" in error_msg:
                QMessageBox.critical(
                    self,
                    "Authentication Failed",
                    "Invalid email or password.\n\nPlease check your credentials and try again."
                )
            elif "Email not confirmed" in error_msg:
                QMessageBox.warning(
                    self,
                    "Email Not Verified",
                    "Please verify your email address before logging in.\n\nCheck your inbox for the verification link."
                )
            else:
                QMessageBox.critical(
                    self,
                    "Login Error",
                    f"An error occurred during login:\n\n{error_msg}"
                )
    
    def show_signup(self):
        """Show signup dialog"""
        signup_dialog = SignupDialog(self.supabase, self)
        if signup_dialog.exec_() == QDialog.Accepted:
            QMessageBox.information(
                self,
                "Success",
                "Account created successfully!\n\nPlease check your email to verify your account, then log in."
            )
    
    def continue_offline(self):
        """Continue in offline mode"""
        reply = QMessageBox.question(
            self,
            "Offline Mode",
            "Continue in offline mode?\n\n"
            "Features not available offline:\n"
            "• Cloud certificate storage\n"
            "• Certificate sync\n"
            "• Online verification\n\n"
            "Local features will still work:\n"
            "• Drive wiping\n"
            "• Local certificate generation\n"
            "• Operation logging",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.user = None
            self.session = None
            self.accept()


class SignupDialog(QDialog):
    """Sign up dialog for new users"""
    
    def __init__(self, supabase_client: Client, parent=None):
        super().__init__(parent)
        self.supabase = supabase_client
        self.setWindowTitle("Create Account")
        self.setFixedSize(400, 500)
        
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2c3e50, stop:1 #3498db);
            }
            QGroupBox {
                background-color: rgba(255, 255, 255, 220);
                border-radius: 10px;
                margin-top: 1em;
                padding: 15px;
            }
            QLabel {
                color: #2c3e50;
            }
            QLineEdit {
                padding: 8px;
                border: 2px solid #3498db;
                border-radius: 5px;
                background-color: white;
                font-size: 12px;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
                min-width: 100px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
        title = QLabel("Create New Account")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setStyleSheet("color: white;")
        layout.addWidget(title)
        
        layout.addSpacing(10)
        
        form_group = QGroupBox("Account Details")
        form_group.setFont(QFont("Segoe UI", 10, QFont.Bold))
        form_layout = QVBoxLayout(form_group)
        form_layout.setSpacing(10)
        
        name_label = QLabel("Full Name:")
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter your full name")
        form_layout.addWidget(name_label)
        form_layout.addWidget(self.name_edit)
        
        email_label = QLabel("Email:")
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("Enter your email")
        form_layout.addWidget(email_label)
        form_layout.addWidget(self.email_edit)
        
        password_label = QLabel("Password:")
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Minimum 6 characters")
        self.password_edit.setEchoMode(QLineEdit.Password)
        form_layout.addWidget(password_label)
        form_layout.addWidget(self.password_edit)
        
        confirm_label = QLabel("Confirm Password:")
        self.confirm_edit = QLineEdit()
        self.confirm_edit.setPlaceholderText("Re-enter password")
        self.confirm_edit.setEchoMode(QLineEdit.Password)
        form_layout.addWidget(confirm_label)
        form_layout.addWidget(self.confirm_edit)
        
        layout.addWidget(form_group)
        layout.addSpacing(10)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Ok).setText("Sign Up")
        button_box.button(QDialogButtonBox.Ok).setFont(QFont("Segoe UI", 10, QFont.Bold))
        button_box.button(QDialogButtonBox.Cancel).setFont(QFont("Segoe UI", 10))
        button_box.accepted.connect(self.signup)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def signup(self):
        """Create new user account"""
        name = self.name_edit.text().strip()
        email = self.email_edit.text().strip()
        password = self.password_edit.text()
        confirm = self.confirm_edit.text()
        
        if not name:
            QMessageBox.warning(self, "Error", "Please enter your full name")
            return
        
        if not email or '@' not in email:
            QMessageBox.warning(self, "Error", "Please enter a valid email address")
            return
        
        if len(password) < 6:
            QMessageBox.warning(self, "Error", "Password must be at least 6 characters")
            return
        
        if password != confirm:
            QMessageBox.warning(self, "Error", "Passwords do not match")
            return
        
        try:
            # Sign up with Supabase
            response = self.supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "full_name": name
                    }
                }
            })
            
            if response.user:
                # Note: User profile will be created automatically by database trigger
                # or after email verification when user first logs in
                self.accept()
            else:
                QMessageBox.critical(
                    self,
                    "Sign Up Failed",
                    "Could not create account. Please try again."
                )
                
        except Exception as e:
            error_msg = str(e)
            
            if "already registered" in error_msg.lower() or "already exists" in error_msg.lower():
                QMessageBox.warning(
                    self,
                    "Email Already Registered",
                    "This email is already registered.\n\nPlease log in or use a different email."
                )
            else:
                QMessageBox.critical(
                    self,
                    "Sign Up Error",
                    f"An error occurred during sign up:\n\n{error_msg}"
                )


class PinDialog(QDialog):
    """PIN setup/entry dialog with Supabase storage"""
    
    def __init__(self, supabase_client: Client = None, user_id: str = None, setup_mode=True):
        super().__init__()
        self.supabase = supabase_client
        self.user_id = user_id
        self.setup_mode = setup_mode
        self.pin = None
        
        self.setWindowTitle("Set Security PIN" if setup_mode else "Enter Security PIN")
        self.setFixedSize(400, 320)
        
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2c3e50, stop:1 #3498db);
            }
            QGroupBox {
                background-color: rgba(255, 255, 255, 220);
                border-radius: 10px;
                margin-top: 1em;
                padding: 15px;
            }
            QLabel {
                color: #2c3e50;
            }
            QLineEdit {
                padding: 8px;
                border: 2px solid #3498db;
                border-radius: 5px;
                background-color: white;
                font-size: 16px;
                text-align: center;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
        icon_label = QLabel()
        icon_label.setPixmap(self.style().standardIcon(
            QStyle.SP_DialogNoButton if self.setup_mode else QStyle.SP_DialogYesButton
        ).pixmap(48, 48))
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)
        
        title = QLabel("Security PIN Setup" if self.setup_mode else "Enter Security PIN")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: white;")
        layout.addWidget(title)
        
        pin_group = QGroupBox()
        pin_layout = QVBoxLayout(pin_group)
        
        instruction_text = "Set a 4-digit PIN to secure the application:" if self.setup_mode else "Enter your 4-digit security PIN:"
        instruction_label = QLabel(instruction_text)
        instruction_label.setFont(QFont("Segoe UI", 10))
        instruction_label.setAlignment(Qt.AlignCenter)
        pin_layout.addWidget(instruction_label)
        
        self.pin_edit = QLineEdit()
        self.pin_edit.setEchoMode(QLineEdit.Password)
        self.pin_edit.setMaxLength(4)
        self.pin_edit.setAlignment(Qt.AlignCenter)
        self.pin_edit.setFont(QFont("Segoe UI", 16))
        pin_layout.addWidget(self.pin_edit)
        
        if self.setup_mode:
            self.confirm_pin_edit = QLineEdit()
            self.confirm_pin_edit.setEchoMode(QLineEdit.Password)
            self.confirm_pin_edit.setMaxLength(4)
            self.confirm_pin_edit.setAlignment(Qt.AlignCenter)
            self.confirm_pin_edit.setFont(QFont("Segoe UI", 16))
            confirm_label = QLabel("Confirm PIN:")
            confirm_label.setFont(QFont("Segoe UI", 10))
            confirm_label.setAlignment(Qt.AlignCenter)
            pin_layout.addWidget(confirm_label)
            pin_layout.addWidget(self.confirm_pin_edit)
        
        layout.addWidget(pin_group)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Ok).setText("Set PIN" if self.setup_mode else "Submit")
        button_box.button(QDialogButtonBox.Ok).setFont(QFont("Segoe UI", 10, QFont.Bold))
        button_box.button(QDialogButtonBox.Cancel).setFont(QFont("Segoe UI", 10))
        button_box.accepted.connect(self.validate_pin)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        self.pin_edit.setFocus()
    
    def validate_pin(self):
        """Validate and save/verify PIN"""
        pin = self.pin_edit.text()
        
        if len(pin) < 4:
            QMessageBox.warning(self, "Error", "PIN must be 4 digits")
            return
        
        if not pin.isdigit():
            QMessageBox.warning(self, "Error", "PIN must contain only numbers")
            return
        
        if self.setup_mode:
            confirm_pin = self.confirm_pin_edit.text()
            if pin != confirm_pin:
                QMessageBox.warning(self, "Error", "PINs do not match")
                return
            
            # Save PIN
            if self.supabase and self.user_id:
                if self.save_pin_to_supabase(pin):
                    self.pin = pin
                    self.accept()
                else:
                    # Fallback to local
                    self.save_pin_locally(pin)
                    self.pin = pin
                    self.accept()
            else:
                self.save_pin_locally(pin)
                self.pin = pin
                self.accept()
        else:
            # Verify PIN
            if self.supabase and self.user_id:
                if self.verify_pin_from_supabase(pin):
                    self.pin = pin
                    self.accept()
                elif self.verify_pin_locally(pin):
                    self.pin = pin
                    self.accept()
                else:
                    QMessageBox.critical(self, "Error", "Incorrect PIN")
            else:
                if self.verify_pin_locally(pin):
                    self.pin = pin
                    self.accept()
                else:
                    QMessageBox.critical(self, "Error", "Incorrect PIN")
    
    def save_pin_to_supabase(self, pin: str) -> bool:
        """Save hashed PIN to Supabase user_profiles"""
        try:
            pin_hash = bcrypt.hashpw(pin.encode('utf-8'), bcrypt.gensalt())
            pin_hash_str = pin_hash.decode('utf-8')
            
            print(f"Attempting to save PIN for user: {self.user_id}")
            
            # Method 1: Try direct update
            try:
                response = self.supabase.table('user_profiles').update({
                    'pin_hash': pin_hash_str
                }).eq('id', self.user_id).execute()
                
                print(f"Update response: {response}")
                
            except Exception as update_err:
                print(f"Update failed: {update_err}")
            
            # Method 2: Verify it was saved by reading it back
            try:
                verify = self.supabase.table('user_profiles')\
                    .select('id, pin_hash')\
                    .eq('id', self.user_id)\
                    .execute()
                
                print(f"Verify response: {verify.data}")
                
                if verify.data and len(verify.data) > 0:
                    saved_hash = verify.data[0].get('pin_hash')
                    if saved_hash:
                        # Verify the hash matches what we just saved
                        if bcrypt.checkpw(pin.encode('utf-8'), saved_hash.encode('utf-8')):
                            print(f"✓ PIN successfully saved and verified!")
                            return True
                        else:
                            print(f"⚠ Hash mismatch after save")
                    else:
                        print(f"⚠ pin_hash is NULL in database")
                else:
                    print(f"⚠ No profile row exists for user {self.user_id}")
                    
                    # Try to create the profile row
                    print(f"Attempting to create profile row...")
                    try:
                        create_response = self.supabase.table('user_profiles').insert({
                            'id': self.user_id,
                            'pin_hash': pin_hash_str
                        }).execute()
                        
                        print(f"Create response: {create_response}")
                        
                        if create_response.data:
                            print(f"✓ Profile created with PIN!")
                            return True
                            
                    except Exception as create_err:
                        print(f"Create failed: {create_err}")
                        
            except Exception as verify_err:
                print(f"Verify failed: {verify_err}")
            
            return False
            
        except Exception as e:
            print(f"✗ PIN save completely failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def verify_pin_from_supabase(self, pin: str) -> bool:
        """Verify PIN against Supabase stored hash"""
        try:
            response = self.supabase.table('user_profiles')\
                .select('pin_hash')\
                .eq('id', self.user_id)\
                .execute()
            
            print(f"PIN check response: {response.data}")  # Debug
            
            if response.data and len(response.data) > 0:
                pin_hash = response.data[0].get('pin_hash')
                if pin_hash:
                    stored_hash = pin_hash.encode('utf-8')
                    result = bcrypt.checkpw(pin.encode('utf-8'), stored_hash)
                    print(f"PIN verification result: {result}")
                    return result
                else:
                    print("No pin_hash found in profile")
            else:
                print("No profile found for user")
            
            return False
        
        except Exception as e:
            print(f"Failed to verify PIN from Supabase: {e}")
            return False
    
    def save_pin_locally(self, pin: str):
        """Save PIN locally (fallback)"""
        settings = QSettings("ZeroTrace", "Application")
        pin_hash = bcrypt.hashpw(pin.encode('utf-8'), bcrypt.gensalt())
        settings.setValue("app_pin_hash", pin_hash.decode('utf-8'))
        print("PIN saved locally")
    
    def verify_pin_locally(self, pin: str) -> bool:
        """Verify PIN against local storage (fallback)"""
        settings = QSettings("ZeroTrace", "Application")
        stored_hash = settings.value("app_pin_hash", "")
        
        if stored_hash:
            try:
                return bcrypt.checkpw(pin.encode('utf-8'), stored_hash.encode('utf-8'))
            except:
                old_pin = settings.value("app_pin", "")
                return pin == old_pin
        
        old_pin = settings.value("app_pin", "")
        return pin == old_pin