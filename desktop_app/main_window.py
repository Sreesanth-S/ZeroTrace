from PyQt5.QtWidgets import (QMainWindow, QPushButton, QLabel, QVBoxLayout, QHBoxLayout, 
                             QMessageBox, QProgressBar, QWidget, QComboBox, QGroupBox, 
                             QStyle, QTextEdit, QFrame)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QTextCursor
from PyQt5.QtWidgets import QApplication
from wipe_engine import WipeEngine, WipeMethod, DriveType
from wipe_thread import WipeThread
from certificate_manager import CertificateManager
from pathlib import Path
from logger import logger
from datetime import datetime
from typing import Dict
import sys
import os

app_font = QFont("Segoe UI", 10)
QApplication.setFont(app_font)

sys.path.append(str(Path(__file__).parent.parent))

# Define stylesheets
DARK_STYLESHEET = """
    /* ================================
    ZeroTrace – Dark Pro Theme
    Modern Cybersecurity UI Style
    ================================ */

    /* ----------- Window Background ----------- */
    QMainWindow {
        background-color: #0D1117;
    }

    /* ----------- GroupBox (Cards) ----------- */
    QGroupBox {
        background-color: #161B22;
        border: 1px solid #21262D;
        border-radius: 12px;
        margin-top: 20px;
        padding: 18px;
        font-family: "Segoe UI";
    }

    QGroupBox::title {
        color: #C9D1D9;
        subcontrol-origin: margin;
        left: 12px;
        padding: 4px 8px;
        font-size: 14px;
        background: transparent;
    }

    /* ----------- Labels ----------- */
    QLabel {
        color: #C9D1D9;
        font-family: "Segoe UI";
        font-size: 11pt;
    }

    /* Subtle warnings */
    QLabel#warningLabel {
        color: #F85149;
        font-weight: bold;
    }

    /* ----------- ComboBox ----------- */
    QComboBox {
        background-color: #0D1117;
        border: 1px solid #30363D;
        padding: 8px;
        border-radius: 6px;
        color: #C9D1D9;
        font-size: 10pt;
    }

    QComboBox:hover {
        border-color: #58A6FF;
    }

    /* Dropdown menu */
    QComboBox QAbstractItemView {
        background-color: #161B22;
        color: #C9D1D9;
        selection-background-color: #238636;
        border: 1px solid #30363D;
    }

    /* ----------- Buttons (General) ----------- */
    QPushButton {
        background-color: #21262D;
        color: #C9D1D9;
        border: 1px solid #30363D;
        padding: 10px 16px;
        border-radius: 8px;
        min-width: 110px;
        font-family: "Segoe UI";
        font-size: 11pt;
    }

    QPushButton:hover {
        border-color: #58A6FF;
        background-color: #30363D;
    }

    QPushButton:disabled {
        background-color: #151A1E;
        color: #6E7681;
        border: 1px solid #1C2128;
    }

    /* ----------- Primary Buttons ----------- */
    #startButton {
        background-color: #238636;
        border: 1px solid #2EA043;
        color: white;
    }

    #startButton:hover {
        background-color: #2EA043;
    }

    #stopButton {
        background-color: #DA3633;
        border: 1px solid #F85149;
        color: white;
    }

    #stopButton:hover {
        background-color: #F85149;
    }

    /* Logout / Cloud buttons */
    #logoutButton {
        background-color: #7435c9;
        border: 1px solid #8e53eb;
        color: white;
    }

    #logoutButton:hover {
        background-color: #8e53eb;
    }

    /* ----------- Progress Bar ----------- */
    QProgressBar {
        background-color: #0D1117;
        border: 1px solid #30363D;
        border-radius: 6px;
        height: 26px;
        color: #C9D1D9;
        text-align: center;
        font-weight: bold;
    }

    QProgressBar::chunk {
        background-color: #00FF99;
        border-radius: 6px;
    }

    /* ----------- TextEdit (Operation Log Console) ----------- */
    QTextEdit {
        background-color: #0D1117;
        color: #00EA6A;
        border: 1px solid #30363D;
        border-radius: 8px;
        padding: 8px;
        font-family: Consolas, monospace;
        font-size: 10pt;
    }

    /* ----------- Scrollbars (Modern Minimal) ----------- */
    QScrollBar:vertical {
        background: #0D1117;
        width: 12px;
        margin: 0px;
    }

    QScrollBar::handle:vertical {
        background: #30363D;
        border-radius: 6px;
    }

    QScrollBar::handle:vertical:hover {
        background: #58A6FF;
    }

    QScrollBar::add-line,
    QScrollBar::sub-line {
        height: 0px;
    }

    /* Horizontal scrollbars */
    QScrollBar:horizontal {
        background: #0D1117;
        height: 12px;
    }

    QScrollBar::handle:horizontal {
        background: #30363D;
        border-radius: 6px;
    }

    QScrollBar::handle:horizontal:hover {
        background: #58A6FF;
    }

    /* ----------- Tooltips ----------- */
    QToolTip {
        background-color: #161B22;
        color: #C9D1D9;
        border: 1px solid #30363D;
        padding: 6px;
        font-size: 10pt;
    }

    #HeaderContainer {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #0E1621, stop:1 #0A0F14);
        padding: 25px;
        border-bottom: 1px solid #1F2937;
    }

    #TitleLabel {
        color: #E6EDF3;
        font-size: 26px;
        font-weight: 700;
        letter-spacing: 1px;
    }

    #SubtitleLabel {
        color: #9BAEC8;
        font-size: 14px;
    }

    #LoggedInLabel {
        color: #00FF99;
        font-size: 13px;
        font-weight: bold;
    }

    #FooterBar {
        background-color: #161B22;
        border-top: 1px solid #21262D;
        padding: 15px 20px;
    }
"""

LIGHT_STYLESHEET = """
    /* ================================
    ZeroTrace – Light Theme
    Clean and Professional UI Style
    ================================ */

    /* ----------- Window Background ----------- */
    QMainWindow {
        background-color: #F8F9FA;
    }

    /* ----------- GroupBox (Cards) ----------- */
    QGroupBox {
        background-color: #FFFFFF;
        border: 1px solid #E1E5E9;
        border-radius: 12px;
        margin-top: 20px;
        padding: 18px;
        font-family: "Segoe UI";
    }

    QGroupBox::title {
        color: #24292F;
        subcontrol-origin: margin;
        left: 12px;
        padding: 4px 8px;
        font-size: 14px;
        background: transparent;
    }

    /* ----------- Labels ----------- */
    QLabel {
        color: #24292F;
        font-family: "Segoe UI";
        font-size: 11pt;
    }

    /* Subtle warnings */
    QLabel#warningLabel {
        color: #CF222E;
        font-weight: bold;
    }

    /* ----------- ComboBox ----------- */
    QComboBox {
        background-color: #FFFFFF;
        border: 1px solid #D1D9E0;
        padding: 8px;
        border-radius: 6px;
        color: #24292F;
        font-size: 10pt;
    }

    QComboBox:hover {
        border-color: #0969DA;
    }

    /* Dropdown menu */
    QComboBox QAbstractItemView {
        background-color: #FFFFFF;
        color: #24292F;
        selection-background-color: #238636;
        border: 1px solid #D1D9E0;
    }

    /* ----------- Buttons (General) ----------- */
    QPushButton {
        background-color: #F6F8FA;
        color: #24292F;
        border: 1px solid #D1D9E0;
        padding: 10px 16px;
        border-radius: 8px;
        min-width: 110px;
        font-family: "Segoe UI";
        font-size: 11pt;
    }

    QPushButton:hover {
        border-color: #0969DA;
        background-color: #F3F4F6;
    }

    QPushButton:disabled {
        background-color: #FAFBFC;
        color: #8C959F;
        border: 1px solid #D1D9E0;
    }

    /* ----------- Primary Buttons ----------- */
    #startButton {
        background-color: #238636;
        border: 1px solid #2EA043;
        color: white;
    }

    #startButton:hover {
        background-color: #2EA043;
    }

    #stopButton {
        background-color: #DA3633;
        border: 1px solid #F85149;
        color: white;
    }

    #stopButton:hover {
        background-color: #F85149;
    }

    /* Logout / Cloud buttons */
    #logoutButton {
        background-color: #8250DF;
        border: 1px solid #8957E5;
        color: white;
    }

    #logoutButton:hover {
        background-color: #8957E5;
    }

    /* ----------- Progress Bar ----------- */
    QProgressBar {
        background-color: #FFFFFF;
        border: 1px solid #D1D9E0;
        border-radius: 6px;
        height: 26px;
        color: #24292F;
        text-align: center;
        font-weight: bold;
    }

    QProgressBar::chunk {
        background-color: #238636;
        border-radius: 6px;
    }

    /* ----------- TextEdit (Operation Log Console) ----------- */
    QTextEdit {
        background-color: #FFFFFF;
        color: #24292F;
        border: 1px solid #D1D9E0;
        border-radius: 8px;
        padding: 8px;
        font-family: Consolas, monospace;
        font-size: 10pt;
    }

    /* ----------- Scrollbars (Modern Minimal) ----------- */
    QScrollBar:vertical {
        background: #F8F9FA;
        width: 12px;
        margin: 0px;
    }

    QScrollBar::handle:vertical {
        background: #D1D9E0;
        border-radius: 6px;
    }

    QScrollBar::handle:vertical:hover {
        background: #0969DA;
    }

    QScrollBar::add-line,
    QScrollBar::sub-line {
        height: 0px;
    }

    /* Horizontal scrollbars */
    QScrollBar:horizontal {
        background: #F8F9FA;
        height: 12px;
    }

    QScrollBar::handle:horizontal {
        background: #D1D9E0;
        border-radius: 6px;
    }

    QScrollBar::handle:horizontal:hover {
        background: #0969DA;
    }

    /* ----------- Tooltips ----------- */
    QToolTip {
        background-color: #FFFFFF;
        color: #24292F;
        border: 1px solid #D1D9E0;
        padding: 6px;
        font-size: 10pt;
    }

    #HeaderContainer {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #FFFFFF, stop:1 #F8F9FA);
        padding: 25px;
        border-bottom: 1px solid #E1E5E9;
    }

    #TitleLabel {
        color: #24292F;
        font-size: 26px;
        font-weight: 700;
        letter-spacing: 1px;
    }

    #SubtitleLabel {
        color: #656D76;
        font-size: 14px;
    }

    #LoggedInLabel {
        color: #238636;
        font-size: 13px;
        font-weight: bold;
    }

    #FooterBar {
        background-color: #FFFFFF;
        border-top: 1px solid #E1E5E9;
        padding: 15px 20px;
    }
"""

try:
    from certificate_manager import CertificateManager
    CERT_MANAGER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Certificate manager not available: {e}")
    CERT_MANAGER_AVAILABLE = False
    CertificateManager = None
    SupabaseDesktopClient = None

class ZeroTraceMainWindow(QMainWindow):
    """Main window of the ZeroTrace application"""
    
    def __init__(self, supabase_client=None, user=None):
        super().__init__()
        self.setWindowTitle("ZeroTrace - Secure Drive Wiper")
        self.setMinimumSize(900, 700)

        # Initialize theme
        self.light_mode = False

        # Initialize wipe engine
        self.wipe_engine = WipeEngine()
        self.wipe_thread = None
        self.current_device = None
        
        # Initialize certificate manager
        self.supabase_client = supabase_client
        self.user = user  # Store the authenticated user
        self.certificate_manager = None
        
        if CERT_MANAGER_AVAILABLE:
            try:
                if self.supabase_client:
                    self.certificate_manager = CertificateManager(self.supabase_client)
                    
                    # Pass the user to certificate manager
                    if self.user:
                        self.certificate_manager.user = self.user
                        logger.info(f"Certificate manager initialized for user: {self.user.email}")
                    else:
                        logger.info("Certificate manager initialized in offline mode")
                else:
                    logger.info("Initializing certificate manager in offline mode")
                    self.certificate_manager = self._init_offline_cert_manager()
            except Exception as e:
                logger.error(f"Certificate manager initialization failed: {e}", exc_info=True)
                self.certificate_manager = None
        
        # Initialize UI components
        self.init_ui()
    
    def _init_offline_cert_manager(self):
        """Initialize certificate manager for offline use"""
        try:
            # Create a mock Supabase client
            class OfflineSupabaseClient:
                def __init__(self):
                    self.user = None
            
            offline_client = OfflineSupabaseClient()
            return CertificateManager(offline_client)
        except Exception as e:
            logger.error(f"Failed to create offline cert manager: {e}")
            return None
        
    def init_ui(self):
        """Initialize the user interface"""
        # Set initial dark theme
        self.setStyleSheet(DARK_STYLESHEET)

        titlebar = QFrame()
        titlebar.setObjectName("TitleBar")

        close_btn = QPushButton("✕")
        max_btn = QPushButton("🗖")
        min_btn = QPushButton("—")

        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(30, 30, 30, 30)

        # Create header section
        header = QGroupBox()
        header_layout = QVBoxLayout(header)
        
        title_layout = QHBoxLayout()

        icon_label = QLabel()
        icon_label.setPixmap(self.style().standardIcon(QStyle.SP_DriveHDIcon).pixmap(48, 48))
        title_layout.addWidget(icon_label)

        title_layout.addStretch()

        title_label = QLabel("ZeroTrace Secure Drive Wiper")
        title_label.setFont(QFont("Segoe UI", 24, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_layout.addWidget(title_label)

        title_layout.addStretch()
        header_layout.addLayout(title_layout)
        
        if self.user:
            login_status = QLabel(f"Logged in as: {self.user.email}")
            login_status.setStyleSheet("color: #2ecc71; font-size: 18px;")
            login_status.setAlignment(Qt.AlignCenter)
            header_layout.addWidget(login_status)
        else:
            login_status = QLabel("⚠️ Offline Mode - Certificates saved locally only")
            login_status.setStyleSheet("color: #f39c12; font-size: 18px;")
            login_status.setAlignment(Qt.AlignCenter)
            header_layout.addWidget(login_status)

        subtitle = QLabel("Hardware & Software Secure Erase Solution")
        subtitle.setFont(QFont("Segoe UI", 12))
        subtitle.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(subtitle)
        
        main_layout.addWidget(header)

        # Create drive selection group
        drive_group = QGroupBox("Drive Selection")
        drive_group.setFont(QFont("Segoe UI", 10, QFont.Bold))
        drive_layout = QVBoxLayout(drive_group)
        
        # Drive combo box row
        drive_section = QHBoxLayout()
        drive_label = QLabel("Select Drive:")
        drive_label.setFont(QFont("Segoe UI", 10))
        self.drive_combo = QComboBox()
        self.drive_combo.setFont(QFont("Segoe UI", 10))
        self.drive_combo.currentIndexChanged.connect(self.on_drive_selected)
        
        self.refresh_button = QPushButton()
        self.refresh_button.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        self.refresh_button.setToolTip("Refresh drive list")
        self.refresh_button.clicked.connect(self.refresh_drives)
        self.refresh_button.setFixedSize(40, 40)
        
        drive_section.addWidget(drive_label)
        drive_section.addWidget(self.drive_combo, 1)
        drive_section.addWidget(self.refresh_button)
        drive_layout.addLayout(drive_section)
        
        # Drive info label
        self.drive_info_label = QLabel("No drive selected")
        self.drive_info_label.setFont(QFont("Segoe UI", 9))
        self.drive_info_label.setWordWrap(True)
        drive_layout.addWidget(self.drive_info_label)
        
        main_layout.addWidget(drive_group)

        # Create wipe method selection group
        method_group = QGroupBox("Wipe Method")
        method_group.setFont(QFont("Segoe UI", 10, QFont.Bold))
        method_layout = QVBoxLayout(method_group)
        
        method_section = QHBoxLayout()
        method_label = QLabel("Method:")
        method_label.setFont(QFont("Segoe UI", 10))
        self.method_combo = QComboBox()
        self.method_combo.setFont(QFont("Segoe UI", 10))
        self.method_combo.currentIndexChanged.connect(self.on_method_changed)
        
        method_section.addWidget(method_label)
        method_section.addWidget(self.method_combo, 1)
        method_layout.addLayout(method_section)
        
        # Method info label
        self.method_info_label = QLabel("Select a drive to see available methods")
        self.method_info_label.setFont(QFont("Segoe UI", 9))
        self.method_info_label.setWordWrap(True)
        method_layout.addWidget(self.method_info_label)
        
        # Warning label
        self.warning_label = QLabel("")
        self.warning_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.warning_label.setStyleSheet("QLabel { color: #e74c3c; }")
        self.warning_label.setWordWrap(True)
        self.warning_label.setVisible(False)
        method_layout.addWidget(self.warning_label)
        
        main_layout.addWidget(method_group)

        # Create progress group
        progress_group = QGroupBox("Wipe Progress")
        progress_group.setFont(QFont("Segoe UI", 10, QFont.Bold))
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFormat("%p% Complete")
        self.progress_bar.setAlignment(Qt.AlignCenter)
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Ready")
        self.status_label.setFont(QFont("Segoe UI", 10))
        self.status_label.setAlignment(Qt.AlignCenter)
        progress_layout.addWidget(self.status_label)
        
        main_layout.addWidget(progress_group)

        # Create log display
        log_group = QGroupBox("Operation Log")
        log_group.setFont(QFont("Segoe UI", 10, QFont.Bold))
        log_layout = QVBoxLayout(log_group)
        
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setMaximumHeight(150)
        log_layout.addWidget(self.log_display)
        
        main_layout.addWidget(log_group)

        # Create footer bar
        footer = QWidget()
        footer.setObjectName("FooterBar")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(20, 10, 20, 10)

        self.start_button = QPushButton("Start Wiping")
        self.start_button.setObjectName("startButton")
        self.start_button.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.start_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.start_button.clicked.connect(self.start_wipe)
        self.start_button.setMinimumHeight(40)

        self.stop_button = QPushButton("Stop")
        self.stop_button.setObjectName("stopButton")
        self.stop_button.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.stop_button.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        self.stop_button.clicked.connect(self.stop_wipe)
        self.stop_button.setEnabled(False)
        self.stop_button.setMinimumHeight(40)

        self.logout_button = QPushButton("Logout")
        self.logout_button.setObjectName("logoutButton")
        self.logout_button.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.logout_button.setIcon(self.style().standardIcon(QStyle.SP_DialogCloseButton))
        self.logout_button.clicked.connect(self.logout)
        self.logout_button.setMinimumHeight(40)

        self.view_certs_button = QPushButton("View Certificates")
        self.view_certs_button.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.view_certs_button.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        self.view_certs_button.clicked.connect(self.view_certificates)
        self.view_certs_button.setMinimumHeight(40)

        # Add this after the "View Certificates" button code:
        self.sync_certs_button = QPushButton("Sync to Cloud")
        self.sync_certs_button.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.sync_certs_button.setIcon(self.style().standardIcon(QStyle.SP_ArrowUp))
        self.sync_certs_button.clicked.connect(self.sync_certificates_to_cloud)
        self.sync_certs_button.setMinimumHeight(40)

        header.setObjectName("HeaderContainer")
        title_label.setObjectName("TitleLabel")
        subtitle.setObjectName("SubtitleLabel")
        login_status.setObjectName("LoggedInLabel")

        self.themeToggle = QPushButton("Light Mode")
        self.themeToggle.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.themeToggle.clicked.connect(self.toggle_theme)
        self.themeToggle.setMinimumHeight(40)

        # Add buttons to footer layout
        footer_layout.addStretch()
        if hasattr(self, 'view_certs_button'):
            footer_layout.addWidget(self.view_certs_button)
        footer_layout.addWidget(self.sync_certs_button)  # Add sync button
        footer_layout.addWidget(self.themeToggle)
        footer_layout.addWidget(self.start_button)
        footer_layout.addWidget(self.stop_button)
        footer_layout.addWidget(self.logout_button)
        footer_layout.addStretch()

        main_layout.addWidget(footer)
        
        # Initialize drives list
        self.refresh_drives()
        self.log("ZeroTrace initialized. Select a drive to begin.")
    
    def log(self, message: str):
        """Add message to log display"""
        self.log_display.append(f"[{self._get_timestamp()}] {message}")
        self.log_display.moveCursor(QTextCursor.End)
    
    def toggle_theme(self):
        if self.light_mode:
            self.setStyleSheet(DARK_STYLESHEET)
            self.themeToggle.setText("☀ Light Mode")
            self.light_mode = False
        else:
            self.setStyleSheet(LIGHT_STYLESHEET)
            self.themeToggle.setText("🌙 Dark Mode")
            self.light_mode = True
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragPos = event.globalPos()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(self.pos() + (event.globalPos() - self.dragPos))
            self.dragPos = event.globalPos()
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")
    
    def refresh_drives(self):
        """Refresh the list of available drives"""
        self.log("Scanning for available drives...")
        self.drive_combo.clear()
        self.current_device = None
        
        drives = self.wipe_engine.get_available_drives()
        
        if not drives:
            self.log("No suitable drives found. Connect a removable drive.")
            self.drive_info_label.setText("No drives available")
            self.method_combo.clear()
            self.method_info_label.setText("No drive selected")
            return
        
        for drive in drives:
            display_text = f"{drive.name} ({drive.size_gb:.2f} GB) - {drive.drive_type.value}"
            self.drive_combo.addItem(display_text, drive)
        
        self.log(f"Found {len(drives)} drive(s)")
    
    def on_drive_selected(self, index: int):
        """Handle drive selection change"""
        if index < 0:
            return
        
        self.current_device = self.drive_combo.itemData(index)
        
        if not self.current_device:
            return
        
        # Update drive info
        info_text = (
            f"Type: {self.current_device.drive_type.value} | "
            f"Size: {self.current_device.size_gb:.2f} GB | "
            f"Model: {self.current_device.model or 'Unknown'} | "
            f"Serial: {self.current_device.serial or 'N/A'}"
        )
        
        if self.current_device.is_frozen:
            info_text += " | ⚠️ FROZEN - Power cycle required"
        
        self.drive_info_label.setText(info_text)
        
        self.log(f"Selected drive: {self.current_device.name}")
        self.log(f"  Type: {self.current_device.drive_type.value}")
        self.log(f"  Size: {self.current_device.size_gb:.2f} GB")
        
        # Update method combo box
        self.update_method_combo()
    
    def update_method_combo(self):
        """Update available wipe methods based on selected drive"""
        self.method_combo.clear()
        
        if not self.current_device:
            return
        
        # Get supported methods
        supported_methods = self.wipe_engine.get_supported_methods(self.current_device)
        
        # Get recommended method
        best_method = self.wipe_engine.detect_best_wipe_method(self.current_device)
        recommended_method = best_method['method']
        
        self.log(f"Recommended method: {recommended_method}")
        self.log(f"  Reason: {best_method['reason']}")
        
        # Populate combo box
        for method in supported_methods:
            if method == recommended_method:
                display_text = f"{method} (Recommended)"
            else:
                display_text = method
            
            self.method_combo.addItem(display_text, method)
        
        # Select recommended method
        for i in range(self.method_combo.count()):
            if self.method_combo.itemData(i) == recommended_method:
                self.method_combo.setCurrentIndex(i)
                break
        
        # Update info label
        self.method_info_label.setText(best_method['reason'])
    
    def on_method_changed(self, index: int):
        """Handle method selection change"""
        if index < 0 or not self.current_device:
            return
        
        selected_method = self.method_combo.itemData(index)
        best_method = self.wipe_engine.detect_best_wipe_method(self.current_device)
        
        # Check if user selected inferior method
        warnings = []
        
        # SSD warnings
        if self.current_device.drive_type in [DriveType.SATA_SSD, DriveType.NVME_SSD]:
            if selected_method in [WipeMethod.DOD_3_PASS, WipeMethod.DOD_7_PASS, WipeMethod.GUTMANN_35_PASS]:
                warnings.append("⚠️ Multi-pass overwrite is not recommended for SSDs and may reduce lifespan.")
        
        # Frozen drive warnings
        if self.current_device.is_frozen:
            if selected_method in [WipeMethod.ATA_SECURE_ERASE, WipeMethod.ATA_ENHANCED_SECURE_ERASE]:
                warnings.append("⚠️ Drive is frozen. ATA Secure Erase will fail. Power cycle the drive first.")
        
        # Incompatible method warnings
        if selected_method == WipeMethod.ATA_SECURE_ERASE and not self.current_device.supports_ata_secure_erase:
            warnings.append("⚠️ This drive does not support ATA Secure Erase.")
        
        if selected_method == WipeMethod.NVME_FORMAT and not self.current_device.supports_nvme_format:
            warnings.append("⚠️ This drive does not support NVMe Format.")
        
        # Show warnings
        if warnings:
            self.warning_label.setText("\n".join(warnings))
            self.warning_label.setVisible(True)
        else:
            self.warning_label.setVisible(False)
        
        # Log method change
        if selected_method != best_method['method']:
            self.log(f"⚠️ Overriding recommended method. Selected: {selected_method}")
    
    def start_wipe(self):
        """Start the drive wiping process"""
        if not self.current_device:
            QMessageBox.warning(self, "No Drive Selected", "Please select a drive first.")
            return
        
        if self.method_combo.currentIndex() < 0:
            QMessageBox.warning(self, "No Method Selected", "Please select a wipe method.")
            return
        
        selected_method = self.method_combo.itemData(self.method_combo.currentIndex())
        
        # Build confirmation message
        confirm_msg = (
            f"⚠️ DESTRUCTIVE OPERATION WARNING ⚠️\n\n"
            f"You are about to PERMANENTLY ERASE ALL DATA on:\n\n"
            f"Drive: {self.current_device.name}\n"
            f"Type: {self.current_device.drive_type.value}\n"
            f"Size: {self.current_device.size_gb:.2f} GB\n"
            f"Path: {self.current_device.path}\n\n"
            f"Method: {selected_method}\n\n"
            f"THIS ACTION CANNOT BE UNDONE!\n\n"
            f"Are you absolutely sure you want to continue?"
        )
        
        reply = QMessageBox.warning(
            self,
            "⚠️ Confirm Destructive Operation",
            confirm_msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            self.log("Wipe operation cancelled by user")
            return
        
        # Disable UI
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.refresh_button.setEnabled(False)
        self.drive_combo.setEnabled(False)
        self.method_combo.setEnabled(False)
        self.logout_button.setEnabled(False)
        
        self.log("="*50)
        self.log(f"Starting wipe operation: {selected_method}")
        self.log(f"Target: {self.current_device.name}")
        self.log("="*50)
        
        # Create and start wipe thread
        self.wipe_thread = WipeThread(
            self.current_device,
            selected_method,
            True
        )
        self.wipe_thread.progress_updated.connect(self.on_progress_update)
        self.wipe_thread.wipe_completed.connect(self.wipe_finished)
        self.wipe_thread.wipe_failed.connect(self.wipe_failed)
        self.wipe_thread.start()
    
    def stop_wipe(self):
        """Stop the drive wiping process"""
        if self.wipe_thread and self.wipe_thread.isRunning():
            reply = QMessageBox.question(
                self,
                "Confirm Stop",
                "Are you sure you want to stop the wiping process?\n\n"
                "Stopping may leave the drive in an inconsistent state.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.log("Stop requested by user...")
                self.wipe_thread.stop()
                self.logout_button.setEnabled(True)
    
    def on_progress_update(self, progress, message):
        """Handle progress update from wipe thread"""
        self.progress_bar.setValue(progress)
        self.status_label.setText(message)
        self.log(message)
    def wipe_failed(self, error_message):
        """Handle wipe failure"""
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.refresh_button.setEnabled(True)
        self.drive_combo.setEnabled(True)
        self.method_combo.setEnabled(True)
        self.logout_button.setEnabled(True)
        self.wipe_thread = None

        self.log("="*50)
        self.log(f"❌ Wipe FAILED: {error_message}")
        self.log("="*50)

        QMessageBox.critical(
            self,
            "❌ Wipe Failed",
            f"An error occurred during wiping:\n\n{error_message}\n\n"
            f"Please check the log for details.",
            QMessageBox.Ok
        )
    
    def wipe_finished(self, result):
        """Handle wipe completion with certificate generation"""
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.refresh_button.setEnabled(True)
        self.drive_combo.setEnabled(True)
        self.method_combo.setEnabled(True)
        self.logout_button.setEnabled(True)
        self.wipe_thread = None
        
        self.log("="*50)
        self.log(f"Wipe completed: {result['status']}")
        self.log(f"Method: {result['method']}")
        self.log(f"Duration: {result['duration']}")
        if result.get('passes_completed'):
            self.log(f"Passes: {result['passes_completed']}")
        if result.get('completion_hash'):
            self.log(f"Hash: {result['completion_hash'][:16]}...")
        self.log("="*50)
        
        # Generate certificate if wipe was successful
        if result.get('success') and result.get('status') == 'Completed':
            self.generate_certificate(result)
        else:
            # Show completion dialog without certificate
            self._show_wipe_complete_without_cert(result)

    def generate_certificate(self, wipe_result: Dict):
        """Generate digital certificate after successful wipe"""
        try:
            self.log("Generating certificate...")
            self.status_label.setText("Generating certificate...")
            
            if not self.certificate_manager:
                self.log("⚠️ Certificate manager not available")
                self._create_simple_certificate(wipe_result)
                return
            
            # Prepare wipe result data for certificate
            # Match the exact structure expected by certificate_manager.py
            cert_wipe_data = {
                'device_id': wipe_result.get('device_id', 'unknown'),
                'device_name': wipe_result.get('device_name', 'Unknown Device'),
                'model': wipe_result.get('device_model', 'N/A'),
                'serial': wipe_result.get('device_serial', 'N/A'),
                'capacity': f"{wipe_result.get('device_size', 0) / (1024**3):.2f} GB",
                'device_type': wipe_result.get('device_type', 'Unknown'),
                'method': wipe_result.get('method', 'Unknown'),
                'passes': wipe_result.get('passes_completed', 1),
                'start_time': wipe_result.get('start_time', datetime.utcnow().isoformat()),
                'end_time': wipe_result.get('end_time', datetime.utcnow().isoformat()),
                'status': wipe_result.get('status', 'Completed'),
                'completion_hash': wipe_result.get('completion_hash', ''),
            }
            
            self.log(f"Certificate data prepared: {cert_wipe_data['device_name']}")
            
            # Generate and sign certificate
            self.log("Creating signed certificate...")
            json_path, pdf_path, cert_data = self.certificate_manager.generate_and_sign_certificate(cert_wipe_data)
            
            self.log(f"✓ Certificate generated: {cert_data['cert_id']}")
            self.log(f"  JSON: {json_path}")
            self.log(f"  PDF: {pdf_path}")
            
            # Try to upload certificate if user is logged in
            uploaded = False
            if self.supabase_client and hasattr(self.supabase_client, 'user') and self.supabase_client.user:
                self.log("Uploading certificate to cloud...")
                try:
                    uploaded = self.certificate_manager.upload_certificate(json_path, pdf_path, cert_data)
                    
                    if uploaded:
                        self.log("✓ Certificate uploaded successfully")
                    else:
                        self.log("⚠️ Certificate upload failed - saved locally")
                except Exception as upload_err:
                    self.log(f"⚠️ Upload error: {upload_err}")
                    uploaded = False
            else:
                self.log("ℹ️ Not logged in - certificate saved locally only")
            
            # Show completion dialog with certificate info
            self._show_wipe_complete_with_cert(wipe_result, cert_data, json_path, pdf_path, uploaded)
            
        except Exception as e:
            logger.error(f"Certificate generation failed: {e}", exc_info=True)
            self.log(f"❌ Certificate generation failed: {str(e)}")
            
            # Try to create simple certificate as fallback
            try:
                self._create_simple_certificate(wipe_result)
            except:
                self._show_wipe_complete_without_cert(wipe_result)

    def _create_simple_certificate(self, wipe_result: Dict):
        """Create a simple text certificate as fallback"""
        try:
            self.log("Creating simple text certificate...")
            
            # Create certificates directory
            cert_dir = Path("certificates")
            cert_dir.mkdir(exist_ok=True)
            
            # Generate simple certificate ID
            import hashlib
            cert_id = hashlib.sha256(
                f"{wipe_result.get('device_id')}_{datetime.now().isoformat()}".encode()
            ).hexdigest()[:16]
            
            # Create text certificate
            cert_content = f"""
ZEROTRACE WIPE CERTIFICATE
{'='*60}

Certificate ID: {cert_id}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

DEVICE INFORMATION:
- Device: {wipe_result.get('device_name', 'Unknown')}
- Model: {wipe_result.get('device_model', 'N/A')}
- Serial: {wipe_result.get('device_serial', 'N/A')}
- Size: {wipe_result.get('device_size', 0) / (1024**3):.2f} GB
- Type: {wipe_result.get('device_type', 'Unknown')}

WIPE DETAILS:
- Method: {wipe_result.get('method', 'Unknown')}
- Status: {wipe_result.get('status', 'Unknown')}
- Passes: {wipe_result.get('passes_completed', 'N/A')}
- Duration: {wipe_result.get('duration', 'N/A')}
- Start: {wipe_result.get('start_time', 'N/A')}
- End: {wipe_result.get('end_time', 'N/A')}

VERIFICATION:
- Hash: {wipe_result.get('completion_hash', 'N/A')}

{'='*60}
This certificate verifies that the above device was securely
wiped using ZeroTrace secure wipe application.
"""
            
            # Save certificate
            cert_path = cert_dir / f"{cert_id}.txt"
            with open(cert_path, 'w') as f:
                f.write(cert_content)
            
            self.log(f"✓ Simple certificate created: {cert_path}")
            
            # Show completion dialog
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("✓ Wipe Complete - Certificate Generated")
            msg.setText("Drive wiping completed successfully!")
            
            details = f"""
<b>Wipe Details:</b>
• Method: {wipe_result['method']}
• Duration: {wipe_result['duration']}
• Status: {wipe_result['status']}

<b>Simple Certificate Generated:</b>
• Certificate ID: {cert_id}
• Location: {cert_path}

Note: Full certificate features require certificate_utils module.
            """
            
            msg.setInformativeText(details)
            msg.setStandardButtons(QMessageBox.Ok)
            
            # Add button to open certificate folder
            open_folder_btn = msg.addButton("Open Certificate Folder", QMessageBox.ActionRole)
            
            msg.exec_()
            
            if msg.clickedButton() == open_folder_btn:
                self._open_certificate_folder(cert_dir)
                
        except Exception as e:
            logger.error(f"Simple certificate creation failed: {e}")
            self._show_wipe_complete_without_cert(wipe_result)

    def _show_wipe_complete_with_cert(self, wipe_result: Dict, cert_data: Dict, 
                                       json_path: Path, pdf_path: Path, uploaded: bool):
        """Show completion dialog with certificate information"""
        upload_status = "✓ Uploaded to cloud" if uploaded else "⚠️ Saved locally only"
        
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("✓ Wipe Complete - Certificate Generated")
        msg.setText("Drive wiping completed successfully!")
        
        details = f"""
<b>Wipe Details:</b>
• Method: {wipe_result['method']}
• Duration: {wipe_result['duration']}
• Passes: {wipe_result.get('passes_completed', 'N/A')}
• Status: {wipe_result['status']}

<b>Certificate Generated:</b>
• Certificate ID: {cert_data['cert_id']}
• Status: {upload_status}

<b>Files Saved:</b>
• JSON: {json_path.name}
• PDF: {pdf_path.name}

<b>Location:</b>
{json_path.parent}
        """
        
        msg.setInformativeText(details)
        msg.setStandardButtons(QMessageBox.Ok)
        
        # Add buttons
        open_folder_btn = msg.addButton("Open Certificate Folder", QMessageBox.ActionRole)
        open_pdf_btn = msg.addButton("View PDF Certificate", QMessageBox.ActionRole)
        
        msg.exec_()
        
        # Handle button clicks
        clicked_button = msg.clickedButton()
        if clicked_button == open_folder_btn:
            self._open_certificate_folder(json_path.parent)
        elif clicked_button == open_pdf_btn:
            self._open_pdf_certificate(pdf_path)

    def _show_wipe_complete_without_cert(self, wipe_result: Dict):
        """Show completion dialog without certificate"""
        if wipe_result.get('success'):
            QMessageBox.information(
                self,
                "✓ Wipe Complete",
                f"Drive wiping completed successfully!\n\n"
                f"Method: {wipe_result.get('method', 'Unknown')}\n"
                f"Duration: {wipe_result.get('duration', 'N/A')}\n"
                f"Status: {wipe_result.get('status', 'Unknown')}\n\n"
                f"Note: Certificate generation was not available.",
                QMessageBox.Ok
            )
        else:
            QMessageBox.warning(
                self,
                "Wipe Completed with Issues",
                f"Wipe operation finished but may not be complete.\n\n"
                f"Status: {wipe_result.get('status', 'Unknown')}\n"
                f"Check the log for details.",
                QMessageBox.Ok
            )

    def _open_certificate_folder(self, folder_path: Path):
        """Open the certificate folder in file explorer"""
        try:
            import subprocess
            import platform
            
            if platform.system() == 'Windows':
                os.startfile(str(folder_path))
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', str(folder_path)])
            else:  # Linux
                subprocess.run(['xdg-open', str(folder_path)])
                
        except Exception as e:
            logger.error(f"Failed to open folder: {e}")
            QMessageBox.warning(
                self,
                "Error",
                f"Could not open folder:\n{folder_path}",
                QMessageBox.Ok
            )

    def _open_pdf_certificate(self, pdf_path: Path):
        """Open the PDF certificate"""
        try:
            import subprocess
            import platform
            
            if not pdf_path.exists():
                raise FileNotFoundError(f"PDF not found: {pdf_path}")
            
            if platform.system() == 'Windows':
                os.startfile(str(pdf_path))
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', str(pdf_path)])
            else:  # Linux
                subprocess.run(['xdg-open', str(pdf_path)])
                
        except Exception as e:
            logger.error(f"Failed to open PDF: {e}")
            QMessageBox.warning(
                self,
                "Error",
                f"Could not open PDF:\n{pdf_path}\n\nError: {str(e)}",
                QMessageBox.Ok
            )
    def view_certificates(self):
            """View local certificates"""
            try:
                cert_dir = Path("certificates")
                
                if not cert_dir.exists():
                    QMessageBox.information(
                        self,
                        "No Certificates",
                        "No certificates directory found.\n\n"
                        "Certificates will be created after successful wipe operations.",
                        QMessageBox.Ok
                    )
                    return
                
                # Get all certificate files
                json_certs = list(cert_dir.glob("*.json"))
                txt_certs = list(cert_dir.glob("*.txt"))
                all_certs = json_certs + txt_certs
                
                if not all_certs:
                    QMessageBox.information(
                        self,
                        "No Certificates",
                        "No certificates found.\n\n"
                        "Certificates are generated after successful wipe operations.",
                        QMessageBox.Ok
                    )
                    return
                
                # Open certificate folder
                self._open_certificate_folder(cert_dir)
                
            except Exception as e:
                logger.error(f"Error viewing certificates: {e}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to view certificates:\n{str(e)}",
                    QMessageBox.Ok
                )
    
    def sync_certificates_to_cloud(self):
        """Sync local certificates to Supabase cloud"""
        if not self.certificate_manager:
            QMessageBox.warning(
                self,
                "Not Available",
                "Certificate manager is not initialized.",
                QMessageBox.Ok
            )
            return
        
        if not self.user:
            QMessageBox.warning(
                self,
                "Not Logged In",
                "You must be logged in to sync certificates to the cloud.\n\n"
                "Please restart the application and log in with your credentials.",
                QMessageBox.Ok
            )
            return
        
        # Confirm sync
        reply = QMessageBox.question(
            self,
            "Sync Certificates",
            "Upload all local certificates to Supabase cloud?\n\n"
            "This will:\n"
            "• Upload all JSON and PDF files\n"
            "• Create database records\n"
            "• Skip certificates already uploaded\n\n"
            "Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Show progress
        self.log("Starting certificate sync...")
        self.status_label.setText("Syncing certificates...")
        
        try:
            # Perform sync
            result = self.certificate_manager.sync_local_certificates()
            
            # Log results
            self.log(f"Sync complete:")
            self.log(f"  • Synced: {result['synced']}")
            self.log(f"  • Skipped: {result['skipped']}")
            self.log(f"  • Failed: {result['failed']}")
            self.log(f"  • Total: {result['total']}")
            
            # Show results dialog
            if result['success']:
                QMessageBox.information(
                    self,
                    "Sync Complete",
                    f"Certificate sync completed!\n\n"
                    f"Synced: {result['synced']}\n"
                    f"Skipped (already uploaded): {result['skipped']}\n"
                    f"Failed: {result['failed']}\n"
                    f"Total processed: {result['total']}",
                    QMessageBox.Ok
                )
            else:
                QMessageBox.warning(
                    self,
                    "Sync Failed",
                    f"Certificate sync failed:\n\n{result.get('message', 'Unknown error')}",
                    QMessageBox.Ok
                )
            
            self.status_label.setText("Ready")
            
        except Exception as e:
            logger.error(f"Sync error: {e}", exc_info=True)
            self.log(f"❌ Sync error: {str(e)}")
            self.status_label.setText("Sync failed")
            QMessageBox.critical(
                self,
                "Error",
                f"An error occurred during sync:\n\n{str(e)}",
                QMessageBox.Ok
            )

    def logout(self):
        """Handle user logout"""
        # Confirm logout
        reply = QMessageBox.question(
            self,
            "Confirm Logout",
            "Are you sure you want to logout?\n\n"
            "Any ongoing operations will be stopped.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.log("User logged out")

            # Stop any ongoing wipe operation
            if self.wipe_thread and self.wipe_thread.isRunning():
                self.wipe_thread.stop()
                self.wipe_thread.wait()  # Wait for thread to finish

            # Close the main window (this will return to login)
            self.close()
