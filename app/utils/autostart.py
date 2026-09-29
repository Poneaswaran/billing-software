"""
Windows Autostart and Background Service Registration Utilities.
"""

import sys
import os

RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_REG_NAME = "ToyPopBilling"


def get_target_command() -> str:
    """Returns the command line string to launch ToyPop Billing in background mode."""
    if getattr(sys, "frozen", False):
        exe_path = sys.executable
        return f'"{exe_path}" --background'
    else:
        # Development fallback pointing to run.py
        current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        run_py = os.path.join(current_dir, "run.py")
        return f'"{sys.executable}" "{run_py}" --background'


def is_autostart_enabled() -> bool:
    """Checks whether ToyPop Billing is configured to start with Windows."""
    if sys.platform != "win32":
        return False

    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, APP_REG_NAME)
            return bool(val)
    except FileNotFoundError:
        return False
    except Exception:
        return False


def set_autostart_enabled(enabled: bool) -> bool:
    """
    Enables or disables ToyPop Billing starting with Windows in background mode.
    Writes to HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run.
    """
    if sys.platform != "win32":
        return False

    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                cmd = get_target_command()
                winreg.SetValueEx(key, APP_REG_NAME, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, APP_REG_NAME)
                except FileNotFoundError:
                    pass
        return True
    except Exception as e:
        print(f"Error configuring autostart registry: {e}")
        return False
