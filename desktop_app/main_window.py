from imports import *
from wipe_engine import WipeEngine
from wipe_thread import WipeThread

class ZeroTraceMainWindow(QMainWindow):
    """Main window of the ZeroTrace application"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ZeroTrace - Secure Drive Wiper")
        self.setMinimumSize(800, 600)
        
        # Initialize wipe engine
        self.wipe_engine = WipeEngine()
        self.wipe_thread = None
        
        # Initialize UI components
        self.init_ui()
        
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
            QComboBox {
                padding: 5px;
                border: 2px solid #3498db;
                border-radius: 5px;
                min-width: 200px;
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
        """)

        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)

        # Create header section
        header = QGroupBox()
        header_layout = QVBoxLayout(header)
        
        # Create title label with icon
        title_layout = QHBoxLayout()
        icon_label = QLabel()
        icon_label.setPixmap(self.style().standardIcon(QStyle.SP_DriveHDIcon).pixmap(48, 48))
        title_layout.addWidget(icon_label)
        
        title_label = QLabel("ZeroTrace Secure Drive Wiper")
        title_label.setFont(QFont("Segoe UI", 24, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_layout.addWidget(title_label)
        title_layout.addSpacing(48)  # Balance the icon space
        header_layout.addLayout(title_layout)
        
        # Add subtitle
        subtitle = QLabel("Secure and permanent data erasure tool")
        subtitle.setFont(QFont("Segoe UI", 12))
        subtitle.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(subtitle)
        
        main_layout.addWidget(header)

        # Create drive selection group
        drive_group = QGroupBox("Drive Selection")
        drive_group.setFont(QFont("Segoe UI", 10, QFont.Bold))
        drive_layout = QVBoxLayout(drive_group)
        
        drive_section = QHBoxLayout()
        drive_label = QLabel("Select Drive:")
        drive_label.setFont(QFont("Segoe UI", 10))
        self.drive_combo = QComboBox()
        self.drive_combo.setFont(QFont("Segoe UI", 10))
        
        self.refresh_button = QPushButton()
        self.refresh_button.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        self.refresh_button.setToolTip("Refresh drive list")
        self.refresh_button.clicked.connect(self.refresh_drives)
        self.refresh_button.setFixedSize(40, 40)
        
        drive_section.addWidget(drive_label)
        drive_section.addWidget(self.drive_combo)
        drive_section.addWidget(self.refresh_button)
        drive_layout.addLayout(drive_section)
        
        main_layout.addWidget(drive_group)

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

        # Create action buttons group
        button_group = QGroupBox("Actions")
        button_group.setFont(QFont("Segoe UI", 10, QFont.Bold))
        button_layout = QHBoxLayout(button_group)
        
        self.start_button = QPushButton("Start Wiping")
        self.start_button.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.start_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.start_button.clicked.connect(self.start_wipe)
        
        self.stop_button = QPushButton("Stop")
        self.stop_button.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.stop_button.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        self.stop_button.clicked.connect(self.stop_wipe)
        self.stop_button.setEnabled(False)
        
        button_layout.addStretch()
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addStretch()
        
        main_layout.addWidget(button_group)
        
        # Add bottom spacing
        main_layout.addStretch()
        
        # Initialize drives list
        self.refresh_drives()
    
    def refresh_drives(self):
        """Refresh the list of available drives"""
        self.drive_combo.clear()
        # Get available drives from wipe engine
        drives = self.wipe_engine.get_available_drives()
        for drive in drives:
            self.drive_combo.addItem(drive)
    
    def start_wipe(self):
        """Start the drive wiping process"""
        if self.drive_combo.currentText():
            reply = QMessageBox.warning(
                self,
                "Confirm Wipe",
                "Are you sure you want to securely wipe this drive?\nThis action cannot be undone!",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.start_button.setEnabled(False)
                self.stop_button.setEnabled(True)
                self.refresh_button.setEnabled(False)
                self.drive_combo.setEnabled(False)

                # Create and start wipe thread
                self.wipe_thread = WipeThread(
                    self.drive_combo.currentText(),
                    'secure',
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
                "Are you sure you want to stop the wiping process?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.wipe_thread.stop()
    
    def update_progress(self, value):
        """Update the progress bar"""
        self.progress_bar.setValue(value)
    
    def on_progress_update(self, progress, message):
        """Handle progress update from wipe thread"""
        self.update_progress(progress)
        self.update_status(message)

    def update_status(self, status):
        """Update the status label"""
        self.status_label.setText(status)

    def wipe_finished(self, log_path):
        """Handle wipe completion"""
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.refresh_button.setEnabled(True)
        self.drive_combo.setEnabled(True)
        self.wipe_thread = None

        QMessageBox.information(
            self,
            "Wipe Complete",
            f"Drive wiping process has completed.\nLog saved to: {log_path}",
            QMessageBox.Ok
        )

    def wipe_failed(self, error_message):
        """Handle wipe failure"""
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.refresh_button.setEnabled(True)
        self.drive_combo.setEnabled(True)
        self.wipe_thread = None

        QMessageBox.critical(
            self,
            "Wipe Failed",
            f"An error occurred during wiping:\n{error_message}",
            QMessageBox.Ok
        )
