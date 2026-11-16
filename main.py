"""
NexiaVPN - Main Entry Point
"""
import sys
import os

# Ensure we're running from the correct directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from ui.main_window import MainWindow
from core.setup_manager import SetupManager
from utils.logger import Logger

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("NexiaVPN")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("NexiaVPN")

    # Set app icon
    icon_path = os.path.join("assets", "icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # High DPI support
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    logger = Logger()
    logger.info("NexiaVPN starting...")

    # Check and setup dependencies
    setup = SetupManager()
    if not setup.check_all():
        setup.show_setup_dialog(app)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
