from PyQt5.QtWidgets import QDialog, QLabel, QVBoxLayout, QLineEdit, QMessageBox, QDialogButtonBox, QGroupBox, QStyle
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QFont

class LoginDialog(QDialog):
    """Login dialog for user authentication"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ZeroTrace Login")
        self.setFixedSize(400, 500)
        self.settings = QSettings("ZeroTrace", "Application")
        
        # Set dialog style
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
        
        # Add some spacing
        layout.addSpacing(20)
        
        # Create login group box
        login_group = QGroupBox("Login Details")
        login_group.setFont(QFont("Segoe UI", 10, QFont.Bold))
        login_layout = QVBoxLayout(login_group)
        login_layout.setSpacing(10)
        
        # Username field
        username_label = QLabel("Username:")
        username_label.setFont(QFont("Segoe UI", 10))
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Enter your username")
        self.username_edit.setFont(QFont("Segoe UI", 10))
        login_layout.addWidget(username_label)
        login_layout.addWidget(self.username_edit)
        
        # Password field
        password_label = QLabel("Password:")
        password_label.setFont(QFont("Segoe UI", 10))
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Enter your password")
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setFont(QFont("Segoe UI", 10))
        login_layout.addWidget(password_label)
        login_layout.addWidget(self.password_edit)
        
        layout.addWidget(login_group)
        
        # Add some spacing
        layout.addSpacing(20)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Ok).setText("Login")
        button_box.button(QDialogButtonBox.Ok).setFont(QFont("Segoe UI", 10, QFont.Bold))
        button_box.button(QDialogButtonBox.Cancel).setFont(QFont("Segoe UI", 10))
        button_box.accepted.connect(self.authenticate)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        
        # Load saved username
        saved_username = self.settings.value("username", "")
        self.username_edit.setText(saved_username)
        
        if saved_username:
            self.password_edit.setFocus()
        else:
            self.username_edit.setFocus()
            
    def validate_pin(self):
        """Validate the entered PIN"""
        pin = self.pin_edit.text()
        
        if not pin.isdigit() or len(pin) != 4:
            QMessageBox.warning(
                self,
                "Invalid PIN",
                "Please enter a 4-digit PIN using numbers only.",
                QMessageBox.Ok
            )
            return
        
        if self.setup_mode:
            confirm_pin = self.confirm_pin_edit.text()
            if pin != confirm_pin:
                QMessageBox.warning(
                    self,
                    "PIN Mismatch",
                    "The PINs you entered do not match. Please try again.",
                    QMessageBox.Ok
                )
                return
                
        self.pin = pin
        self.accept()
    
    def authenticate(self):
        username = self.username_edit.text()
        password = self.password_edit.text()
        
        # Simple authentication (in real app, this would be proper authentication)
        if username and password:
            # Save username
            self.settings.setValue("username", username)
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "Please enter both username and password")

class PinDialog(QDialog):
    """PIN setup/entry dialog"""
    
    def __init__(self, setup_mode=True):
        super().__init__()
        self.setup_mode = setup_mode
        self.setWindowTitle("Set Security PIN" if setup_mode else "Enter Security PIN")
        self.setFixedSize(400, 300)
        
        # Set dialog style
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
            QDialogButtonBox {
                button-layout: center;
            }
        """)
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Icon
        icon_label = QLabel()
        icon_label.setPixmap(self.style().standardIcon(QStyle.SP_DialogNoButton if self.setup_mode else QStyle.SP_DialogYesButton).pixmap(48, 48))
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)
        
        # Title
        title = QLabel("Security PIN Setup" if self.setup_mode else "Enter Security PIN")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        layout.addWidget(title)
        
        # Create PIN group box
        pin_group = QGroupBox()
        pin_group.setFont(QFont("Segoe UI", 10))
        pin_layout = QVBoxLayout(pin_group)
        
        # Instructions
        instruction_text = "Set a 4-digit PIN to secure the application:" if self.setup_mode else "Enter your 4-digit security PIN:"
        instruction_label = QLabel(instruction_text)
        instruction_label.setFont(QFont("Segoe UI", 10))
        instruction_label.setAlignment(Qt.AlignCenter)
        pin_layout.addWidget(instruction_label)
        
        # PIN input
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
        
        # Buttons
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
        pin = self.pin_edit.text()
        
        if len(pin) < 4:
            QMessageBox.warning(self, "Error", "PIN must be at least 4 characters")
            return
        
        if self.setup_mode:
            confirm_pin = self.confirm_pin_edit.text()
            if pin != confirm_pin:
                QMessageBox.warning(self, "Error", "PINs do not match")
                return
        
        self.pin = pin
        self.accept()