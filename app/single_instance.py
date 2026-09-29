"""
Single Instance & Fast Wake-up Engine for ToyPop POS & Billing.

Features:
- Windows Named Pipe IPC via PyQt6 QLocalServer / QLocalSocket.
- Ultra-fast wake-up (<50ms) when user clicks the desktop shortcut.
- Windows native foreground activation (SW_RESTORE + SetForegroundWindow).
- Win32 Mutex integration for installer detection and conflict prevention.
"""

import sys
import os
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

IPC_SERVER_NAME = "toypop_billing_single_instance_ipc_2026"
APP_MUTEX_NAME = "ToyPopBilling_App_Mutex_2026"


class SingleInstanceClient:
    """Fast client that detects and activates an existing running instance."""

    @staticmethod
    def try_activate_running_instance(timeout_ms: int = 400) -> bool:
        """
        Attempts to connect to an existing running instance of ToyPop Billing.
        If found, sends the SHOW wake-up command and returns True.
        If no instance is running, returns False.
        """
        socket = QLocalSocket()
        socket.connectToServer(IPC_SERVER_NAME)

        if not socket.waitForConnected(timeout_ms):
            return False

        # Connected to existing background/foreground instance!
        try:
            socket.write(b"SHOW\n")
            socket.flush()
            socket.waitForBytesWritten(300)
            # Wait briefly for acknowledgment
            if socket.waitForReadyRead(300):
                socket.readAll()
            socket.disconnectFromServer()
            return True
        except Exception:
            return False


class SingleInstanceServer(QObject):
    """
    Local IPC server hosted by the primary background instance.
    Listens for wake-up requests and triggers window activation.
    """

    show_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.server = None
        self._mutex_handle = None
        self._init_mutex()
        self._start_server()

    def _init_mutex(self):
        """Creates a named Win32 mutex so Inno Setup installer knows the app is running."""
        try:
            import ctypes
            from ctypes import wintypes

            kernel32 = ctypes.windll.kernel32
            # CreateMutexW(security_attributes, initial_owner, name)
            self._mutex_handle = kernel32.CreateMutexW(None, False, APP_MUTEX_NAME)
        except Exception:
            pass

    def _start_server(self):
        # Remove any stale local server pipe from previous unexpected termination
        QLocalServer.removeServer(IPC_SERVER_NAME)
        self.server = QLocalServer(self)
        self.server.newConnection.connect(self._on_new_connection)

        if not self.server.listen(IPC_SERVER_NAME):
            # Try cleaning up once more if address in use
            QLocalServer.removeServer(IPC_SERVER_NAME)
            self.server.listen(IPC_SERVER_NAME)

    def _on_new_connection(self):
        while self.server.hasPendingConnections():
            client_socket = self.server.nextPendingConnection()
            if client_socket:
                client_socket.waitForReadyRead(300)
                cmd = bytes(client_socket.readAll()).decode("utf-8", errors="ignore").strip()

                if cmd == "QUIT":
                    client_socket.write(b"OK_QUIT\n")
                    client_socket.flush()
                    client_socket.disconnectFromServer()
                    self.quit_requested.emit()
                else:
                    # Default: SHOW or ACTIVATE
                    client_socket.write(b"OK_SHOW\n")
                    client_socket.flush()
                    client_socket.disconnectFromServer()
                    self.show_requested.emit()

    def close(self):
        if self.server:
            self.server.close()
            QLocalServer.removeServer(IPC_SERVER_NAME)
            self.server = None
        if self._mutex_handle:
            try:
                import ctypes
                ctypes.windll.kernel32.CloseHandle(self._mutex_handle)
                self._mutex_handle = None
            except Exception:
                pass


def force_activate_window(window):
    """
    Brings the window to the front, restores it if minimized/hidden,
    and forces Windows foreground focus.
    """
    if window is None:
        return

    # Show window if hidden
    if not window.isVisible():
        window.show()

    # Restore if minimized
    if window.isMinimized():
        window.showNormal()

    window.raise_()
    window.activateWindow()

    # Native Windows API foreground boost
    if sys.platform == "win32":
        try:
            import ctypes
            hwnd = int(window.winId())
            user32 = ctypes.windll.user32
            # SW_RESTORE = 9, SW_SHOW = 5
            user32.ShowWindow(hwnd, 9)
            user32.SetForegroundWindow(hwnd)
        except Exception:
            pass
