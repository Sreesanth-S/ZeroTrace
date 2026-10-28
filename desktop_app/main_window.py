from PyQt5.QtWidgets import (QMainWindow, QPushButton, QLabel, QVBoxLayout, QHBoxLayout, 
                             QMessageBox, QProgressBar, QWidget, QComboBox, QGroupBox, 
                             QStyle, QTextEdit, QFrame, QScrollArea, QApplication)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QTextCursor, QIcon, QPixmap
from wipe_engine import WipeEngine, WipeMethod, DriveType, get_compliance_info
from wipe_thread import WipeThread
from backend_client import backend_client
from pathlib import Path
from datetime import datetime
from typing import Dict
import sys
import logging

LOGO_PATH = Path(__file__).parent / "assets" / "ZeroTrace.png"

logger = logging.getLogger("ZeroTrace")

sys.path.append(str(Path(__file__).parent.parent))

# Modern, Unified Single Stylesheet
MODERN_STYLESHEET = """
    /* =========================================================================
       ZeroTrace — Authoritative Modern Single Stylesheet
       Clean, scalable, high-contrast dark cybersecurity design system
       ========================================================================= */

    /* Global Windows, Dialogs, and Base Widgets */
    QMainWindow, QWidget#ContentWidget, QDialog, QMessageBox {
        background-color: #0A0E17;
        color: #F8FAFC;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }

    /* Message Boxes - High Contrast, Crystal Clear Text */
    QMessageBox {
        background-color: #0F172A;
        border: 1px solid #1E293B;
    }

    QMessageBox QLabel {
        color: #F8FAFC;
        font-size: 10.5pt;
        font-weight: 500;
        background: transparent;
        min-height: 32px;
    }

    QMessageBox QPushButton {
        background-color: #1E293B;
        color: #F8FAFC;
        border: 1px solid #334155;
        border-radius: 6px;
        padding: 8px 20px;
        font-size: 10pt;
        font-weight: 600;
        min-width: 80px;
    }

    QMessageBox QPushButton:hover {
        background-color: #2D3D54;
        border-color: #38BDF8;
        color: #FFFFFF;
    }

    QMessageBox QPushButton:pressed {
        background-color: #0A0E17;
    }

    /* Scroll Area */
    QScrollArea#MainScrollArea {
        background-color: transparent;
        border: none;
    }

    /* Group Boxes (Cards) */
    QGroupBox {
        background-color: #111827;
        border: 1px solid #1F293D;
        border-radius: 10px;
        margin-top: 14px;
        padding: 14px 16px 14px 16px;
        font-size: 10.5pt;
        font-weight: 600;
        color: #94A3B8;
    }

    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 14px;
        padding: 0 6px;
        color: #38BDF8;
        background-color: transparent;
        font-size: 10pt;
        font-weight: 600;
        letter-spacing: 0.3px;
    }

    /* Labels */
    QLabel {
        color: #CBD5E1;
        font-size: 10pt;
        background: transparent;
    }

    QLabel#TitleLabel {
        color: #F8FAFC;
        font-size: 16pt;
        font-weight: 700;
        letter-spacing: 0.5px;
    }

    QLabel#SubtitleLabel {
        color: #64748B;
        font-size: 9.5pt;
        font-weight: 400;
    }

    QLabel#LoggedInLabel {
        color: #10B981;
        font-size: 10pt;
        font-weight: 600;
    }

    QLabel#WarningLabel {
        color: #F87171;
        font-size: 9.5pt;
        font-weight: 600;
    }

    /* Header Container Card */
    QGroupBox#HeaderContainer {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #0F172A, stop:1 #111827);
        border: 1px solid #1E293B;
        border-radius: 12px;
        margin-top: 0px;
        padding: 16px 20px;
    }

    /* ComboBox */
    QComboBox {
        background-color: #0F172A;
        border: 1px solid #334155;
        border-radius: 6px;
        padding: 7px 12px;
        color: #F1F5F9;
        font-size: 10pt;
        min-height: 22px;
    }

    QComboBox:hover {
        border-color: #38BDF8;
        background-color: #131E33;
    }

    QComboBox:focus {
        border-color: #38BDF8;
    }

    QComboBox::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 24px;
        border-left: 1px solid #1E293B;
    }

    QComboBox QAbstractItemView {
        background-color: #0F172A;
        border: 1px solid #334155;
        border-radius: 6px;
        color: #F1F5F9;
        selection-background-color: #1E293B;
        selection-color: #38BDF8;
        outline: none;
        padding: 4px;
    }

    /* Buttons */
    QPushButton {
        background-color: #1E293B;
        color: #F1F5F9;
        border: 1px solid #334155;
        border-radius: 7px;
        padding: 8px 16px;
        font-size: 10pt;
        font-weight: 600;
        min-width: 90px;
        min-height: 20px;
    }

    QPushButton:hover {
        background-color: #2D3D54;
        border-color: #475569;
    }

    QPushButton:pressed {
        background-color: #1A2433;
    }

    QPushButton:disabled {
        background-color: #0F172A;
        color: #475569;
        border-color: #1E293B;
    }

    /* Primary Action Buttons */
    QPushButton#startButton {
        background-color: #059669;
        border: 1px solid #10B981;
        color: #FFFFFF;
        padding: 9px 22px;
        font-size: 10pt;
    }

    QPushButton#startButton:hover {
        background-color: #10B981;
        border-color: #34D399;
    }

    QPushButton#startButton:pressed {
        background-color: #047857;
    }

    QPushButton#startButton:disabled {
        background-color: #064E3B;
        border-color: #064E3B;
        color: #6EE7B7;
    }

    QPushButton#stopButton {
        background-color: #DC2626;
        border: 1px solid #EF4444;
        color: #FFFFFF;
        padding: 9px 20px;
        font-size: 10pt;
    }

    QPushButton#stopButton:hover {
        background-color: #EF4444;
        border-color: #F87171;
    }

    QPushButton#stopButton:pressed {
        background-color: #B91C1C;
    }

    QPushButton#stopButton:disabled {
        background-color: #1E293B;
        border-color: #334155;
        color: #475569;
    }

    QPushButton#logoutButton {
        background-color: #334155;
        border: 1px solid #475569;
        color: #E2E8F0;
        padding: 9px 18px;
        font-size: 10pt;
    }

    QPushButton#logoutButton:hover {
        background-color: #475569;
        border-color: #64748B;
        color: #FFFFFF;
    }

    QPushButton#exitButton {
        background-color: #1E293B;
        border: 1px solid #475569;
        color: #E2E8F0;
        padding: 9px 18px;
        font-size: 10pt;
    }

    QPushButton#exitButton:hover {
        background-color: #991B1B;
        border-color: #EF4444;
        color: #FFFFFF;
    }

    QPushButton#exitButton:pressed {
        background-color: #7F1D1D;
    }

    QPushButton#refreshButton {
        min-width: 38px;
        max-width: 38px;
        min-height: 34px;
        max-height: 34px;
        padding: 0px;
    }

    /* Progress Bar */
    QProgressBar {
        background-color: #0F172A;
        border: 1px solid #1E293B;
        border-radius: 6px;
        height: 22px;
        color: #F8FAFC;
        text-align: center;
        font-size: 9.5pt;
        font-weight: 600;
    }

    QProgressBar::chunk {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #059669, stop:1 #10B981);
        border-radius: 5px;
    }

    /* Operation Log Console */
    QTextEdit {
        background-color: #06090F;
        color: #34D399;
        border: 1px solid #1E293B;
        border-radius: 8px;
        padding: 10px;
        font-family: "Consolas", "Cascadia Code", "Courier New", monospace;
        font-size: 9pt;
        line-height: 1.4;
    }

    /* Footer Dock */
    QWidget#FooterBar {
        background-color: #0B111E;
        border-top: 1px solid #1E293B;
        padding: 12px 20px;
    }

    /* Modern Minimalist Scrollbars */
    QScrollBar:vertical {
        background: #0A0E17;
        width: 10px;
        margin: 0px;
    }

    QScrollBar::handle:vertical {
        background: #1E293B;
        min-height: 30px;
        border-radius: 5px;
    }

    QScrollBar::handle:vertical:hover {
        background: #38BDF8;
    }

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }

    QScrollBar:horizontal {
        background: #0A0E17;
        height: 10px;
        margin: 0px;
    }

    QScrollBar::handle:horizontal {
        background: #1E293B;
        min-width: 30px;
        border-radius: 5px;
    }

    QScrollBar::handle:horizontal:hover {
        background: #38BDF8;
    }

    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0px;
    }

    /* Tooltip */
    QToolTip {
        background-color: #1E293B;
        color: #F8FAFC;
        border: 1px solid #334155;
        border-radius: 4px;
        padding: 5px 8px;
        font-size: 9.5pt;
    }

    /* CheckBoxes */
    QCheckBox {
        color: #94A3B8;
        font-size: 9.5pt;
        spacing: 8px;
    }

    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border-radius: 4px;
        border: 1px solid #475569;
        background: #0F172A;
    }

    QCheckBox::indicator:hover {
        border-color: #38BDF8;
    }

    QCheckBox::indicator:checked {
        background-color: #0284C7;
        border-color: #38BDF8;
        image: url("''' + (Path(__file__).parent / "assets" / "checkmark.png").resolve().as_posix() + '''");
    }
"""

class ZeroTraceMainWindow(QMainWindow):
    """Main window of the ZeroTrace application"""
    
    def __init__(self, backend_client_instance=None, user=None, session=None, **kwargs):
        super().__init__()
        self.setWindowTitle("ZeroTrace - Secure Drive Wiper")
        self.setMinimumSize(780, 560)
        self.resize(960, 680)
        self.logged_out = False

        # Initialize wipe engine
        self.wipe_engine = WipeEngine()
        self.wipe_thread = None
        self.current_device = None
        
        # Initialize backend client
        self.backend_client = backend_client_instance or kwargs.get("supabase_client") or backend_client
        self.user = user or getattr(self.backend_client, 'user', None)
        self.session = session or getattr(self.backend_client, 'session', None)
        self.supabase_client = self.backend_client  # Compatibility alias
        
        user_email = getattr(self.user, 'email', str(self.user)) if self.user else "Authenticated User"
        logger.info(f"ZeroTrace initialized for user: {user_email}")
        
        # Initialize UI components
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface with responsive scalable layouts"""
        if LOGO_PATH.exists():
            self.setWindowIcon(QIcon(str(LOGO_PATH)))

        # Apply modern single stylesheet
        self.setStyleSheet(MODERN_STYLESHEET)

        # Root container and vertical layout
        root_widget = QWidget()
        self.setCentralWidget(root_widget)
        root_layout = QVBoxLayout(root_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Scroll area for scalable content (prevents text clipping on small/minimized window)
        scroll_area = QScrollArea()
        scroll_area.setObjectName("MainScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Scrollable content widget
        content_widget = QWidget()
        content_widget.setObjectName("ContentWidget")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(14)
        content_layout.setContentsMargins(24, 20, 24, 16)

        # Header section
        header = QGroupBox()
        header.setObjectName("HeaderContainer")
        header_layout = QVBoxLayout(header)
        header_layout.setSpacing(6)
        
        title_layout = QHBoxLayout()

        icon_label = QLabel()
        if LOGO_PATH.exists():
            icon_label.setPixmap(QPixmap(str(LOGO_PATH)).scaled(42, 42, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            icon_label.setPixmap(self.style().standardIcon(QStyle.SP_DriveHDIcon).pixmap(40, 40))
        title_layout.addWidget(icon_label)

        title_layout.addStretch()

        title_label = QLabel("ZeroTrace Secure Drive Wiper")
        title_label.setObjectName("TitleLabel")
        title_label.setAlignment(Qt.AlignCenter)
        title_layout.addWidget(title_label)

        title_layout.addStretch()
        header_layout.addLayout(title_layout)
        
        user_email = getattr(self.user, 'email', str(self.user)) if self.user else "User"
        login_status = QLabel(f"Logged in as: {user_email}")
        login_status.setObjectName("LoggedInLabel")
        login_status.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(login_status)

        subtitle = QLabel("Hardware & Software Secure Erase Solution")
        subtitle.setObjectName("SubtitleLabel")
        subtitle.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(subtitle)
        
        content_layout.addWidget(header)

        # Drive selection group
        drive_group = QGroupBox("Drive Selection")
        drive_layout = QVBoxLayout(drive_group)
        drive_layout.setSpacing(10)
        
        drive_section = QHBoxLayout()
        drive_label = QLabel("Select Drive:")
        self.drive_combo = QComboBox()
        self.drive_combo.currentIndexChanged.connect(self.on_drive_selected)
        
        self.refresh_button = QPushButton()
        self.refresh_button.setObjectName("refreshButton")
        self.refresh_button.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        self.refresh_button.setToolTip("Refresh drive list")
        self.refresh_button.clicked.connect(self.refresh_drives)
        
        drive_section.addWidget(drive_label)
        drive_section.addWidget(self.drive_combo, 1)
        drive_section.addWidget(self.refresh_button)
        drive_layout.addLayout(drive_section)
        
        # Drive info label
        self.drive_info_label = QLabel("No drive selected")
        self.drive_info_label.setWordWrap(True)
        drive_layout.addWidget(self.drive_info_label)
        
        content_layout.addWidget(drive_group)

        # Wipe method selection group
        method_group = QGroupBox("Wipe Method")
        method_layout = QVBoxLayout(method_group)
        method_layout.setSpacing(10)
        
        method_section = QHBoxLayout()
        method_label = QLabel("Method:")
        self.method_combo = QComboBox()
        self.method_combo.currentIndexChanged.connect(self.on_method_changed)
        
        method_section.addWidget(method_label)
        method_section.addWidget(self.method_combo, 1)
        method_layout.addLayout(method_section)
        
        # Method info label
        self.method_info_label = QLabel("Select a drive to see available methods")
        self.method_info_label.setWordWrap(True)
        method_layout.addWidget(self.method_info_label)
        
        # Warning label
        self.warning_label = QLabel("")
        self.warning_label.setObjectName("WarningLabel")
        self.warning_label.setWordWrap(True)
        self.warning_label.setVisible(False)
        method_layout.addWidget(self.warning_label)
        
        content_layout.addWidget(method_group)

        # Progress group
        progress_group = QGroupBox("Wipe Progress")
        progress_layout = QVBoxLayout(progress_group)
        progress_layout.setSpacing(8)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFormat("%p% Complete")
        self.progress_bar.setAlignment(Qt.AlignCenter)
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignCenter)
        progress_layout.addWidget(self.status_label)
        
        content_layout.addWidget(progress_group)

        # Operation Log group
        log_group = QGroupBox("Operation Log")
        log_layout = QVBoxLayout(log_group)
        
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setMinimumHeight(90)
        self.log_display.setMaximumHeight(160)
        log_layout.addWidget(self.log_display)
        
        content_layout.addWidget(log_group)

        # Add scroll area to root layout
        scroll_area.setWidget(content_widget)
        root_layout.addWidget(scroll_area, 1)

        # Docked footer bar
        footer = QWidget()
        footer.setObjectName("FooterBar")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(20, 10, 20, 10)
        footer_layout.setSpacing(12)

        self.start_button = QPushButton("Start Wiping")
        self.start_button.setObjectName("startButton")
        self.start_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.start_button.clicked.connect(self.start_wipe)
        self.start_button.setMinimumHeight(38)

        self.stop_button = QPushButton("Stop")
        self.stop_button.setObjectName("stopButton")
        self.stop_button.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        self.stop_button.clicked.connect(self.stop_wipe)
        self.stop_button.setEnabled(False)
        self.stop_button.setMinimumHeight(38)

        self.logout_button = QPushButton("Logout")
        self.logout_button.setObjectName("logoutButton")
        self.logout_button.setIcon(self.style().standardIcon(QStyle.SP_DialogCloseButton))
        self.logout_button.clicked.connect(self.logout)
        self.logout_button.setMinimumHeight(38)

        self.exit_button = QPushButton("Exit")
        self.exit_button.setObjectName("exitButton")
        self.exit_button.setIcon(self.style().standardIcon(QStyle.SP_TitleBarCloseButton))
        self.exit_button.clicked.connect(self.exit_app)
        self.exit_button.setMinimumHeight(38)

        footer_layout.addStretch()
        footer_layout.addWidget(self.start_button)
        footer_layout.addWidget(self.stop_button)
        footer_layout.addWidget(self.logout_button)
        footer_layout.addWidget(self.exit_button)
        footer_layout.addStretch()

        root_layout.addWidget(footer, 0)
        
        # Initialize drives list
        self.refresh_drives()
        self.log("ZeroTrace initialized. Select a drive to begin.")
    
    def log(self, message: str):
        """Add message to log display and stream to runtime log console tab"""
        self.log_display.append(f"[{self._get_timestamp()}] {message}")
        self.log_display.moveCursor(QTextCursor.End)
        logger.info(message)
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        return datetime.now().strftime("%H:%M:%S")
    
    def refresh_drives(self):
        """Refresh the list of available drives with visual loading feedback"""
        self.refresh_button.setEnabled(False)
        self.drive_combo.setEnabled(False)
        orig_tooltip = self.refresh_button.toolTip()
        self.refresh_button.setToolTip("Scanning drives... Please wait")
        self.status_label.setText("⏳ Scanning system for available drives... Please wait")
        QApplication.processEvents()

        try:
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
        finally:
            self.refresh_button.setEnabled(True)
            self.drive_combo.setEnabled(True)
            self.refresh_button.setToolTip(orig_tooltip)
            if not (self.wipe_thread and self.wipe_thread.isRunning()):
                self.status_label.setText("Ready")
    
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
        if getattr(self.current_device, 'hpa_enabled', False):
            info_text += f" | Hidden sectors: {self.current_device.hpa_hidden_sectors}"
        
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
            comp = get_compliance_info(method)
            tag = f" [{comp['level']}]"
            if method == recommended_method:
                display_text = f"{method}{tag} (Recommended)"
            else:
                display_text = f"{method}{tag}"
            
            self.method_combo.addItem(display_text, method)
        
        # Select recommended method
        for i in range(self.method_combo.count()):
            if self.method_combo.itemData(i) == recommended_method:
                self.method_combo.setCurrentIndex(i)
                break
        
        # Update info label
        comp = get_compliance_info(recommended_method)
        comp_summary = f"Standards: {comp['nist_800_88']} | {comp['ieee_2883']} | {comp['dod_5220_22_m']}\n{best_method['reason']}"
        self.method_info_label.setText(comp_summary)
    
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
            if selected_method in [WipeMethod.DOD_3_PASS, WipeMethod.DOD_7_PASS]:
                warnings.append("Software multi-pass wipes can reduce SSD lifespan and may be unnecessary.")

        # hidden sector method information
        if selected_method == WipeMethod.HIDDEN_SECTORS:
            if getattr(self.current_device, 'hpa_enabled', False):
                warnings.append(f"Drive has {self.current_device.hpa_hidden_sectors} hidden sectors; only those will be erased.")
            else:
                warnings.append("No hidden sectors detected; this operation will do nothing.")
        
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
        if not self.backend_client or not self.backend_client.check_connection():
            QMessageBox.critical(
                self,
                "No Internet Connection",
                "Cannot start wipe: Server is unreachable.\n\n"
                "An active internet connection to the server is required to perform wiping and issue certificates."
            )
            return

        if not self.current_device:
            QMessageBox.warning(self, "No Drive Selected", "Please select a drive first.")
            return
        
        if self.method_combo.currentIndex() < 0:
            QMessageBox.warning(self, "No Method Selected", "Please select a wipe method.")
            return
        
        selected_method = self.method_combo.itemData(self.method_combo.currentIndex())
        
        # Build confirmation message
        hidden_note = "* Only hidden (HPA/DCO) areas will be erased. Visible data will be untouched.\n\n" if selected_method == WipeMethod.HIDDEN_SECTORS else ""
        confirm_msg = (
            "⚠️ DESTRUCTIVE OPERATION WARNING ⚠️\n\n"
            "You are about to PERMANENTLY ERASE ALL DATA on:\n\n"
            f"Drive: {self.current_device.name}\n"
            f"Type: {self.current_device.drive_type.value}\n"
            f"Size: {self.current_device.size_gb:.2f} GB\n"
            f"Path: {self.current_device.path}\n\n"
            f"Method: {selected_method}\n\n"
            f"{hidden_note}"
            "THIS ACTION CANNOT BE UNDONE!\n\n"
            "Are you absolutely sure you want to continue?"
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
        
        # Disable UI & indicate loading
        self.start_button.setEnabled(False)
        self.start_button.setText("Starting Wipe...")
        self.stop_button.setEnabled(True)
        self.stop_button.setText("Stop")
        self.refresh_button.setEnabled(False)
        self.drive_combo.setEnabled(False)
        self.method_combo.setEnabled(False)
        self.logout_button.setEnabled(False)
        self.status_label.setText("⏳ Initializing wipe operation... Please wait")
        QApplication.processEvents()

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
                self.stop_button.setEnabled(False)
                self.stop_button.setText("Stopping...")
                self.status_label.setText("⏳ Aborting wipe operation... Please wait")
                QApplication.processEvents()
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
        self.start_button.setText("Start Wiping")
        self.start_button.setEnabled(True)
        self.stop_button.setText("Stop")
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
        self.start_button.setText("Start Wiping")
        self.start_button.setEnabled(True)
        self.stop_button.setText("Stop")
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
        
        # Submit evidence to authoritative backend if wipe succeeded
        if result.get('success') and result.get('status') == 'Completed':
            self.generate_certificate(result)
        else:
            QMessageBox.warning(
                self,
                "Wipe Incomplete",
                f"Drive wipe finished with status: {result.get('status', 'Unknown')}\n\n"
                f"Method: {result.get('method', 'Unknown')}\n"
                f"Duration: {result.get('duration', 'N/A')}\n\n"
                f"Check the activity log for details.",
                QMessageBox.Ok
            )

    def generate_certificate(self, wipe_result: Dict):
        """Submit wipe evidence to authoritative backend and obtain signed certificate"""
        self.status_label.setText("⏳ Submitting wipe evidence to server... Please wait")
        QApplication.processEvents()
        try:
            self.log("Submitting wipe evidence to server...")
            
            # Submit evidence to FastAPI backend
            res = self.backend_client.submit_wipe_result(wipe_result)
            
            if res.get("success"):
                cert_id = res["cert_id"]
                cert_data = res.get("certificate", {})
                sanitization_level = res.get("sanitization_level", "Clear")
                download_url = res.get("download_url")
                
                self.log(f"✓ Certificate issued: {cert_id}")
                self.log(f"  Sanitization Level: {sanitization_level}")
                if download_url:
                    self.log(f"  Download URL: {download_url}")
                
                self._show_wipe_complete_with_cert(
                    wipe_result, cert_data, cert_id, sanitization_level
                )
            else:
                err_msg = res.get("error", "Evidence submission rejected. Evidence doesn't follow Evidence policy")
                self.log(f"❌ Backend rejected evidence: {err_msg}")
                QMessageBox.critical(
                    self,
                    "Certificate Issuance Failed",
                    f"Drive wipe completed, but certificate issuance failed:\n\n{err_msg}\n\n"
                    "An active internet connection to the server is required.",
                    QMessageBox.Ok
                )
        except Exception as e:
            logger.error(f"Evidence submission failed: {e}", exc_info=True)
            self.log(f"❌ Error during evidence submission: {e}")
            QMessageBox.critical(
                self,
                "Submission Error",
                f"Drive wipe completed, but evidence submission to the server encountered an error:\n\n{e}",
                QMessageBox.Ok
            )
        finally:
            self.status_label.setText("Ready")

    def _show_wipe_complete_with_cert(self, wipe_result: Dict, cert_data: Dict, 
                                       cert_id: str, sanitization_level: str = "Clear"):
        """Show completion dialog with backend certificate information"""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("✓ Wipe Complete - Certificate Issued")
        msg.setText("Drive wiping completed successfully and certificate was issued!")
        
        details = f"""
<b>Wipe Details:</b>
• Method: {wipe_result['method']}
• Duration: {wipe_result['duration']}
• Passes: {wipe_result.get('passes_completed', 'N/A')}
• Status: {wipe_result['status']}

<b>Certificate:</b>
• Certificate ID: {cert_id}
• Sanitization Level: {sanitization_level}
• Status: ✓ Verified & Issued by ZeroTrace Cloud
        """
        
        msg.setInformativeText(details)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    def logout(self):
        """Handle user logout: clears credentials and returns to login page"""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Question)
        msg.setWindowTitle("Confirm Logout")
        msg.setText("Are you sure you want to log out?")
        msg.setInformativeText("Logging out will clear your saved session and return to the login screen.")
        yes_btn = msg.addButton("Yes, Logout", QMessageBox.YesRole)
        cancel_btn = msg.addButton("Cancel", QMessageBox.NoRole)
        msg.setDefaultButton(cancel_btn)
        msg.exec_()

        if msg.clickedButton() == yes_btn:
            self.logout_button.setText("Logging out...")
            self.logout_button.setEnabled(False)
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.exit_button.setEnabled(False)
            self.refresh_button.setEnabled(False)
            self.status_label.setText("⏳ Clearing session and logging out... Please wait")
            QApplication.processEvents()

            self.log("User logged out")

            # Stop any ongoing wipe operation
            if self.wipe_thread and self.wipe_thread.isRunning():
                self.wipe_thread.stop()
                self.wipe_thread.wait()

            # Authoritatively clear the persisted session
            if self.backend_client:
                self.backend_client.sign_out()

            self.logged_out = True
            self.close()

    def exit_app(self):
        """Handle application exit: persists login session like a browser and closes the app"""
        if self.wipe_thread and self.wipe_thread.isRunning():
            reply = QMessageBox.warning(
                self,
                "Wipe in Progress",
                "A drive wipe operation is currently running!\n\n"
                "Are you sure you want to stop wiping and exit ZeroTrace?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

            self.exit_button.setText("Exiting...")
            self.exit_button.setEnabled(False)
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.logout_button.setEnabled(False)
            self.refresh_button.setEnabled(False)
            self.status_label.setText("⏳ Exiting ZeroTrace... Please wait")
            QApplication.processEvents()
            self.wipe_thread.stop()
            self.wipe_thread.wait()
        else:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Question)
            msg.setWindowTitle("Exit ZeroTrace")
            msg.setText("Are you sure you want to exit ZeroTrace?")
            msg.setInformativeText("Your login session will be remembered when you reopen the app.")
            exit_btn = msg.addButton("Exit", QMessageBox.AcceptRole)
            cancel_btn = msg.addButton("Cancel", QMessageBox.RejectRole)
            msg.setDefaultButton(exit_btn)
            msg.exec_()

            if msg.clickedButton() != exit_btn:
                return

            self.exit_button.setText("Exiting...")
            self.exit_button.setEnabled(False)
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.logout_button.setEnabled(False)
            self.refresh_button.setEnabled(False)
            self.status_label.setText("⏳ Exiting ZeroTrace... Please wait")
            QApplication.processEvents()

        self.log("Exiting application (session persisted)...")
        self.logged_out = False  # Keep session persisted
        self.close()
        QApplication.quit()

    def closeEvent(self, event):
        """Window close event: prompt if wipe is active; preserve session if not logged out"""
        if self.wipe_thread and self.wipe_thread.isRunning():
            reply = QMessageBox.warning(
                self,
                "Wipe in Progress",
                "A wipe operation is currently running. Stopping now may leave the drive in an inconsistent state.\n\n"
                "Are you sure you want to stop and close?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                event.ignore()
                return

            self.wipe_thread.stop()
            self.wipe_thread.wait()

        event.accept()
