from PyQt5.QtWidgets import (QDialog, QLabel, QVBoxLayout, QLineEdit, QMessageBox, 
                             QDialogButtonBox, QGroupBox, QStyle, QPushButton, QCheckBox,
                             QApplication)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QFont, QIcon, QPixmap
from dotenv import load_dotenv
from pathlib import Path
from backend_client import backend_client, UserProxy, check_internet_connection

load_dotenv()

# Absolute path to checkmark and logo assets
CHECKMARK_ICON_PATH = (Path(__file__).parent / "assets" / "checkmark.png").resolve().as_posix()
LOGO_ICON_PATH = (Path(__file__).parent / "assets" / "ZeroTrace.png").resolve()

# Modern, Unified Dialog Stylesheet
DIALOG_STYLESHEET = f"""
    QDialog, QMessageBox {{
        background-color: #0F172A;
        color: #F8FAFC;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }}
    QMessageBox QLabel {{
        color: #F8FAFC;
        font-size: 10.5pt;
        font-weight: 500;
        background: transparent;
        min-height: 32px;
    }}
    QGroupBox {{
        background-color: #111827;
        border: 1px solid #1E293B;
        border-radius: 10px;
        margin-top: 14px;
        padding: 16px;
        color: #38BDF8;
        font-weight: 600;
        font-size: 10pt;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 12px;
        padding: 0 4px;
        color: #38BDF8;
    }}
    QLabel {{
        color: #CBD5E1;
        font-size: 10pt;
        background: transparent;
    }}
    QLineEdit {{
        background-color: #0F172A;
        border: 1px solid #334155;
        border-radius: 6px;
        padding: 8px 12px;
        color: #F8FAFC;
        font-size: 10pt;
    }}
    QLineEdit:focus {{
        border-color: #38BDF8;
        background-color: #131E33;
    }}
    QPushButton {{
        background-color: #0284C7;
        color: #FFFFFF;
        border: 1px solid #0EA5E9;
        border-radius: 6px;
        padding: 8px 16px;
        font-weight: 600;
        font-size: 10pt;
        min-width: 90px;
    }}
    QPushButton:hover {{
        background-color: #0369A1;
        border-color: #38BDF8;
    }}
    QPushButton:pressed {{
        background-color: #075985;
    }}
    QPushButton:disabled {{
        background-color: #1E293B;
        color: #64748B;
        border-color: #334155;
    }}
    QCheckBox {{
        color: #94A3B8;
        font-size: 9.5pt;
        spacing: 8px;
    }}
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 4px;
        border: 1px solid #475569;
        background: #0F172A;
    }}
    QCheckBox::indicator:hover {{
        border-color: #38BDF8;
    }}
    QCheckBox::indicator:checked {{
        background-color: #0284C7;
        border-color: #38BDF8;
        image: url("{CHECKMARK_ICON_PATH}");
    }}
"""

class LoginDialog(QDialog):
    """Login dialog with FastAPI backend authentication"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ZeroTrace Login")
        self.setMinimumSize(400, 520)
        self.settings = QSettings("ZeroTrace", "Application")
        
        # Initialize Backend client
        self.backend = backend_client
        self.supabase = self.backend
        self.supabase_available = True
        
        self.user = None
        self.session = None
        
        # Apply modern unified dialog style
        self.setStyleSheet(DIALOG_STYLESHEET)
        if LOGO_ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(LOGO_ICON_PATH)))
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Logo/Title section
        icon_label = QLabel()
        if LOGO_ICON_PATH.exists():
            icon_label.setPixmap(QPixmap(str(LOGO_ICON_PATH)).scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
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
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignCenter)
        self.update_connection_status()
        layout.addWidget(self.status_label)
        
        layout.addSpacing(10)
        
        # Create login group box
        login_group = QGroupBox("Login Details")
        login_group.setFont(QFont("Segoe UI", 10, QFont.Bold))
        login_layout = QVBoxLayout(login_group)
        login_layout.setSpacing(10)
        
        # Email field
        email_label = QLabel("Email:")
        email_label.setFont(QFont("Segoe UI", 10))
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("Enter your email")
        self.email_edit.setFont(QFont("Segoe UI", 10))
        login_layout.addWidget(email_label)
        login_layout.addWidget(self.email_edit)
        
        # Password field
        password_label = QLabel("Password:")
        password_label.setFont(QFont("Segoe UI", 10))
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Enter your password")
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setFont(QFont("Segoe UI", 10))
        login_layout.addWidget(password_label)
        login_layout.addWidget(self.password_edit)
        
        # Remember me checkbox
        self.remember_me = QCheckBox("Remember email")
        login_layout.addWidget(self.remember_me)
        
        layout.addWidget(login_group)
        
        layout.addSpacing(10)
        
        # Buttons
        button_box = QDialogButtonBox()
        
        self.login_btn = QPushButton("Login")
        self.login_btn.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.login_btn.clicked.connect(self.authenticate)
        
        self.signup_btn = QPushButton("Sign Up")
        self.signup_btn.setFont(QFont("Segoe UI", 10))
        self.signup_btn.clicked.connect(self.show_signup)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setFont(QFont("Segoe UI", 10))
        self.cancel_btn.clicked.connect(self.reject)
        
        button_box.addButton(self.login_btn, QDialogButtonBox.AcceptRole)
        button_box.addButton(self.signup_btn, QDialogButtonBox.ActionRole)
        button_box.addButton(self.cancel_btn, QDialogButtonBox.RejectRole)
        
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
    
    def update_connection_status(self) -> bool:
        """Check internet & backend reachability and update status label."""
        has_internet = check_internet_connection()
        if not has_internet:
            self.status_label.setText("✕ No Internet Connection")
            self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
            self.status_label.setVisible(True)
            return False

        if self.backend.check_connection():
            self.status_label.setText("")
            self.status_label.setVisible(False)
            return True
        else:
            self.status_label.setText("✕ Server Unreachable")
            self.status_label.setStyleSheet("color: #e67e22; font-weight: bold;")
            self.status_label.setVisible(True)
            return False

    def authenticate(self):
        """Authenticate user with FastAPI backend with visual loading indicator"""
        email = self.email_edit.text().strip()
        password = self.password_edit.text()
        
        if not email or not password:
            QMessageBox.warning(self, "Error", "Please enter both email and password")
            return
        
        if '@' not in email:
            QMessageBox.warning(self, "Error", "Please enter a valid email address")
            return
        
        # Show immediate loading state
        self.login_btn.setEnabled(False)
        self.signup_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.login_btn.setText("Loading...")
        QApplication.processEvents()

        try:
            if not check_internet_connection():
                self.update_connection_status()
                QMessageBox.critical(
                    self, 
                    "No Internet Connection", 
                    "Please connect your device to the internet and try again."
                )
                return

            if not self.backend.check_connection():
                self.update_connection_status()
                QMessageBox.critical(
                    self, 
                    "Server Connection Error", 
                    "Cannot connect to the server.\n\n"
                    "Please verify your network connection"
                )
                return
            
            success = backend_client.sign_in(email, password)
            if success:
                self.user = UserProxy(backend_client.user)
                self.session = backend_client.session
                
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
                self.update_connection_status()
                QMessageBox.critical(
                    self,
                    "Authentication Failed",
                    "Invalid email or password"
                )
                    
        except Exception as e:
            self.update_connection_status()
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
        finally:
            self.login_btn.setText("Login")
            self.login_btn.setEnabled(True)
            self.signup_btn.setEnabled(True)
            self.cancel_btn.setEnabled(True)
            self.update_connection_status()
    
    def show_signup(self):
        """Show signup dialog with loading feedback"""
        self.signup_btn.setEnabled(False)
        self.signup_btn.setText("Loading...")
        QApplication.processEvents()

        try:
            if not check_internet_connection():
                self.update_connection_status()
                QMessageBox.critical(
                    self,
                    "No Internet Connection",
                    "Please connect your device to the internet and try again."
                )
                return

            if not self.backend.check_connection():
                self.update_connection_status()
                QMessageBox.critical(
                    self,
                    "Server Unreachable",
                    "Cannot connect to the server."
                )
                return

            signup_dialog = SignupDialog(self.supabase, self)
            if signup_dialog.exec_() == QDialog.Accepted:
                QMessageBox.information(
                    self,
                    "Success",
                    "Account created successfully!\n\nPlease check your email to verify your account, then log in."
                )
        finally:
            self.signup_btn.setText("Sign Up")
            self.signup_btn.setEnabled(True)


class SignupDialog(QDialog):
    """Sign up dialog for new users"""
    
    def __init__(self, backend_client=None, parent=None):
        super().__init__(parent)
        self.supabase = backend_client
        self.setWindowTitle("Create Account")
        if LOGO_ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(LOGO_ICON_PATH)))
        self.setMinimumSize(400, 520)
        self.setStyleSheet(DIALOG_STYLESHEET)
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
        
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.signup_btn = self.button_box.button(QDialogButtonBox.Ok)
        self.signup_btn.setText("Sign Up")
        self.signup_btn.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.cancel_btn = self.button_box.button(QDialogButtonBox.Cancel)
        self.cancel_btn.setFont(QFont("Segoe UI", 10))
        self.button_box.accepted.connect(self.signup)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
        
        self.setLayout(layout)
    
    def signup(self):
        """Create new user account with visual loading state"""
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
        
        # Show immediate loading state
        self.signup_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.signup_btn.setText("Loading...")
        QApplication.processEvents()

        try:
            if not check_internet_connection():
                QMessageBox.critical(
                    self,
                    "No Internet Connection",
                    "Please connect your device to the internet and try again."
                )
                return

            from backend_client import backend_client
            if not backend_client.check_connection():
                QMessageBox.critical(
                    self,
                    "Server Unreachable",
                    "Cannot connect to the server."
                )
                return
            success = backend_client.sign_up(email, password, name)
            if success:
                QMessageBox.information(
                    self,
                    "Account Created",
                    "Your account has been created successfully. You can now log in."
                )
                self.accept()
            else:
                QMessageBox.critical(
                    self,
                    "Sign Up Failed",
                    "Could not create account. Please check your details and try again."
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
        finally:
            self.signup_btn.setText("Sign Up")
            self.signup_btn.setEnabled(True)
            self.cancel_btn.setEnabled(True)