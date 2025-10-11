import os
import sys
from pathlib import Path
import win32api
import win32file
import win32con
import random
import time
import string

from PyQt5.QtWidgets import (
    QDialog, QApplication, QMainWindow, QPushButton, QLabel, 
    QVBoxLayout, QHBoxLayout, QLineEdit, QMessageBox, QProgressBar, 
    QWidget, QComboBox, QDialogButtonBox, QFrame, QGroupBox,
    QSpacerItem, QSizePolicy, QStyle
)
from PyQt5.QtCore import Qt, QSettings, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor, QLinearGradient