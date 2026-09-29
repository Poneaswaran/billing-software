import sys
import os

# Add parent directory to sys.path so app modules are properly found
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.single_instance import SingleInstanceClient, SingleInstanceServer, force_activate_window
from app.utils.logger import app_logger


def main():
    # -------------------------------------------------------------
    # 1. ULTRA-FAST WAKE-UP CHECK (< 50ms)
    # If the user clicked the desktop shortcut and a background instance
    # is already pre-warmed in memory, immediately wake it up and exit!
    # -------------------------------------------------------------
    is_background = "--background" in sys.argv or "--silent" in sys.argv or "--tray" in sys.argv

    if not is_background:
        try:
            if SingleInstanceClient.try_activate_running_instance(timeout_ms=300):
                app_logger.info("Wake-up signal sent to pre-warmed background instance. Exiting launcher.")
                print("ToyPop Billing: Active instance woke up instantly.")
                sys.exit(0)
        except Exception as e:
            app_logger.warning(f"Error checking single-instance client: {e}")

    # -------------------------------------------------------------
    # 2. PRIMARY APPLICATION STARTUP
    # -------------------------------------------------------------
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QIcon
        from app.db import init_db
        from app.sync import ensure_db_columns
        from app.ui_main import MainWindow
        from app.ui_styles import apply_theme_to_app
        from app.models import SettingsModel

        # Initialize Database and cloud columns
        init_db()
        ensure_db_columns()
        app_logger.info("Database initialized successfully.")

        # Start Qt Application
        app = QApplication(sys.argv)
        app.setApplicationName("ToyPop POS & Billing")
        app.setStyle("Fusion")

        # Set application icon if present
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "assets", "icon.ico")
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))

        theme = SettingsModel.get_setting("theme", "Light")
        touch_mode = SettingsModel.get_setting("touch_mode", "false").lower() == "true"
        apply_theme_to_app(app, theme, touch_mode)

        # Create Main Window
        window = MainWindow()

        # Start Single Instance IPC Server to accept future instant wake-up calls
        server = SingleInstanceServer(window)
        server.show_requested.connect(window.show_and_activate)
        server.quit_requested.connect(window.force_quit_app)
        window.single_instance_server = server

        if is_background:
            app_logger.info("ToyPop Billing started in background service mode (pre-warmed for instant launch).")
            # Do NOT call window.show(); window remains in memory ready for instantaneous opening!
        else:
            window.show()
            window.raise_()
            window.activateWindow()
            app_logger.info("ToyPop Billing main window displayed.")

        sys.exit(app.exec())
    except Exception as e:
        app_logger.critical(f"Application failed to start: {e}", exc_info=True)
        print(f"Critical Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
