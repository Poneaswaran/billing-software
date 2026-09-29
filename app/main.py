import sys
import os
from PyQt6.QtWidgets import QApplication
from app.db import init_db
from app.ui_main import MainWindow
from app.utils.logger import app_logger

from app.ui_styles import apply_theme_to_app
from app.models import SettingsModel

def main():
    try:
        # Initialize Database
        init_db()
        app_logger.info("Database initialized.")

        # Start App
        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        
        theme = SettingsModel.get_setting('theme', 'Light')
        touch_mode = SettingsModel.get_setting('touch_mode', 'false').lower() == 'true'
        apply_theme_to_app(app, theme, touch_mode)
        
        window = MainWindow()
        window.show()
        
        app_logger.info("Application started.")
        sys.exit(app.exec())
    except Exception as e:
        app_logger.critical(f"Application failed to start: {e}")
        print(f"Critical Error: {e}")

if __name__ == "__main__":
    main()
