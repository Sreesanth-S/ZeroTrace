# desktop_app/main_window.py
from PyQt5.QtWidgets import (QMainWindow, QPushButton, QLabel, QVBoxLayout, QHBoxLayout, 
                             QMessageBox, QProgressBar, QWidget, QComboBox, QGroupBox, 
                             QStyle, QTextEdit, QSplitter, QDialog, QListWidget, QListWidgetItem)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QTextCursor
from wipe_engine import WipeEngine, WipeMethod, DriveType
from wipe_thread import WipeThread
from certificate_manager import CertificateManager
from pathlib import Path
from logger import logger
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict
from wipe_engine import WipeEngine, WipeMethod, DriveType
from wipe_thread import WipeThread
from logger import logger

sys.path.append(str(Path(__file__).parent.parent))

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
    
    def __init__(self, supabase_client=None):
        super().__init__()
        self.setWindowTitle("ZeroTrace - Secure Drive Wiper")
        self.setMinimumSize(900, 700)
        
        # Initialize wipe engine
        self.wipe_engine = WipeEngine()
        self.wipe_thread = None
        self.current_device = None
        
        # Initialize certificate manager
        self.supabase_client = supabase_client
        self.certificate_manager = None

        # Disable close button (X button in title bar)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowCloseButtonHint)
        
        if CERT_MANAGER_AVAILABLE:
            try:
                if self.supabase_client:
                    self.certificate_manager = CertificateManager(self.supabase_client)
                    logger.info("Certificate manager initialized with Supabase")
                else:
                    # Create dummy Supabase client for offline mode
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
        # Set window style
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2c3e50, stop:1 #3498db);
            }
            QGroupBox {
                background-color: rgba(255, 255, 255, 220);
                border-radius: 10px;
                margin-top: 1em;
                padding: 15px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                color: #2c3e50;
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
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
            QPushButton#startButton {
                background-color: #27ae60;
            }
            QPushButton#startButton:hover {
                background-color: #229954;
            }
            QPushButton#stopButton {
                background-color: #e74c3c;
            }
            QPushButton#stopButton:hover {
                background-color: #c0392b;
            }
            QComboBox {
                padding: 5px;
                border: 2px solid #3498db;
                border-radius: 5px;
                min-width: 200px;
                background-color: white;
            }
            QLabel {
                color: #2c3e50;
            }
            QProgressBar {
                border: 2px solid #3498db;
                border-radius: 5px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #2ecc71;
                border-radius: 3px;
            }
            QTextEdit {
                background-color: #2c3e50;
                color: #ecf0f1;
                border: 2px solid #34495e;
                border-radius: 5px;
                font-family: 'Courier New';
                font-size: 9pt;
            }
        """)

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
        
        title_label = QLabel("ZeroTrace Secure Drive Wiper")
        title_label.setFont(QFont("Segoe UI", 24, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_layout.addWidget(title_label)
        title_layout.addSpacing(48)
        header_layout.addLayout(title_layout)
        
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

        # Create action buttons group
        button_group = QGroupBox("Actions")
        button_group.setFont(QFont("Segoe UI", 10, QFont.Bold))
        button_layout = QHBoxLayout(button_group)

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

        button_layout.addStretch()
        button_layout.addWidget(self.view_certs_button)
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addWidget(self.logout_button)
        button_layout.addStretch()

        main_layout.addWidget(button_group)
        
        # Initialize drives list
        self.refresh_drives()
        self.log("ZeroTrace initialized. Select a drive to begin.")
    
    def log(self, message: str):
        """Add message to log display"""
        self.log_display.append(f"[{self._get_timestamp()}] {message}")
        self.log_display.moveCursor(QTextCursor.End)
    
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
