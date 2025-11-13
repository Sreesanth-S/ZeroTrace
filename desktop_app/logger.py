# desktop_app/logger.py
"""
Centralized logging system for ZeroTrace Desktop Application
"""

import logging
import os
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler

class ZeroTraceLogger:
    """Singleton logger for the application"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        
        # Create logs directory in AppData
        if os.name == 'nt':  # Windows
            app_data = os.getenv('APPDATA')
            log_dir = Path(app_data) / 'ZeroTrace' / 'logs'
        else:
            log_dir = Path.home() / '.zerotrace' / 'logs'
        
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Log file path
        log_file = log_dir / 'app.log'
        
        # Create logger
        self.logger = logging.getLogger('ZeroTrace')
        self.logger.setLevel(logging.DEBUG)
        
        # Prevent duplicate handlers
        if self.logger.handlers:
            return
        
        # File handler with rotation (10MB max, keep 5 backups)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        self.info(f"Logger initialized. Log file: {log_file}")
    
    def debug(self, message: str):
        """Log debug message"""
        self.logger.debug(message)
    
    def info(self, message: str):
        """Log info message"""
        self.logger.info(message)
    
    def warning(self, message: str):
        """Log warning message"""
        self.logger.warning(message)
    
    def error(self, message: str, exc_info=False):
        """Log error message"""
        self.logger.error(message, exc_info=exc_info)
    
    def critical(self, message: str, exc_info=False):
        """Log critical message"""
        self.logger.critical(message, exc_info=exc_info)
    
    def log_wipe_start(self, device: str, method: str):
        """Log wipe operation start"""
        self.info(f"Wipe operation started - Device: {device}, Method: {method}")
    
    def log_wipe_progress(self, device: str, progress: int):
        """Log wipe progress"""
        self.debug(f"Wipe progress - Device: {device}, Progress: {progress}%")
    
    def log_wipe_complete(self, device: str, status: str, duration: str):
        """Log wipe operation completion"""
        self.info(f"Wipe operation completed - Device: {device}, Status: {status}, Duration: {duration}")
    
    def log_certificate_generated(self, cert_id: str, device: str):
        """Log certificate generation"""
        self.info(f"Certificate generated - ID: {cert_id}, Device: {device}")
    
    def log_certificate_uploaded(self, cert_id: str):
        """Log certificate upload"""
        self.info(f"Certificate uploaded to Supabase - ID: {cert_id}")
    
    def log_auth_event(self, event: str, user_email: str = None):
        """Log authentication event"""
        if user_email:
            self.info(f"Auth event: {event} - User: {user_email}")
        else:
            self.info(f"Auth event: {event}")
    
    def log_error_with_context(self, operation: str, error: Exception):
        """Log error with full context"""
        self.error(f"Error during {operation}: {str(error)}", exc_info=True)


# Global logger instance
logger = ZeroTraceLogger()