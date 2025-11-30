from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, 
    QComboBox, QTabWidget, QWidget, QLabel
)
from app.models import SettingsModel
from app.printer import PrinterManager

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(500, 400)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.tabs = QTabWidget()

        # Store Settings
        self.store_tab = QWidget()
        self.store_layout = QFormLayout()
        self.store_name = QLineEdit(SettingsModel.get_setting('store_name', 'Thangam Stores'))
        self.store_address = QLineEdit(SettingsModel.get_setting('store_address', ''))
        self.store_phone = QLineEdit(SettingsModel.get_setting('store_phone', ''))
        self.store_layout.addRow("Store Name:", self.store_name)
        self.store_layout.addRow("Address:", self.store_address)
        self.store_layout.addRow("Phone:", self.store_phone)
        self.store_tab.setLayout(self.store_layout)
        self.tabs.addTab(self.store_tab, "Store Info")

        # Printer Settings
        self.printer_tab = QWidget()
        self.printer_layout = QFormLayout()
        
        self.printer_type = QComboBox()
        self.printer_type.addItems(["USB", "Serial", "Network", "Dummy"])
        self.printer_type.setCurrentText(SettingsModel.get_setting('printer_type', 'USB'))
        
        self.printer_vid = QLineEdit(SettingsModel.get_setting('printer_usb_vid', ''))
        self.printer_pid = QLineEdit(SettingsModel.get_setting('printer_usb_pid', ''))
        self.printer_port = QLineEdit(SettingsModel.get_setting('printer_serial_port', 'COM1'))
        self.printer_ip = QLineEdit(SettingsModel.get_setting('printer_ip', '192.168.1.100'))
        
        self.printer_layout.addRow("Type:", self.printer_type)
        self.printer_layout.addRow("USB VID (Hex):", self.printer_vid)
        self.printer_layout.addRow("USB PID (Hex):", self.printer_pid)
        self.printer_layout.addRow("Serial Port:", self.printer_port)
        self.printer_layout.addRow("Network IP:", self.printer_ip)
        
        self.printer_tab.setLayout(self.printer_layout)
        self.tabs.addTab(self.printer_tab, "Printer")

        # Email Settings
        self.email_tab = QWidget()
        self.email_layout = QFormLayout()
        self.smtp_server = QLineEdit(SettingsModel.get_setting('smtp_server', ''))
        self.smtp_port = QLineEdit(SettingsModel.get_setting('smtp_port', '587'))
        self.smtp_user = QLineEdit(SettingsModel.get_setting('smtp_user', ''))
        self.smtp_pass = QLineEdit(SettingsModel.get_setting('smtp_pass', ''))
        self.smtp_pass.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.email_layout.addRow("SMTP Server:", self.smtp_server)
        self.email_layout.addRow("SMTP Port:", self.smtp_port)
        self.email_layout.addRow("Email User:", self.smtp_user)
        self.email_layout.addRow("Email Pass:", self.smtp_pass)
        self.email_tab.setLayout(self.email_layout)
        self.tabs.addTab(self.email_tab, "Email")

        # Appearance Settings
        self.appearance_tab = QWidget()
        self.appearance_layout = QFormLayout()
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark"])
        self.theme_combo.setCurrentText(SettingsModel.get_setting('theme', 'Light'))
        self.appearance_layout.addRow("Theme:", self.theme_combo)
        self.appearance_tab.setLayout(self.appearance_layout)
        self.tabs.addTab(self.appearance_tab, "Appearance")

        layout.addWidget(self.tabs)

        self.save_btn = QPushButton("Save Settings")
        self.save_btn.clicked.connect(self.save_settings)
        layout.addWidget(self.save_btn)

        self.setLayout(layout)

    def save_settings(self):
        SettingsModel.set_setting('store_name', self.store_name.text())
        SettingsModel.set_setting('store_address', self.store_address.text())
        SettingsModel.set_setting('store_phone', self.store_phone.text())
        
        SettingsModel.set_setting('printer_type', self.printer_type.currentText())
        SettingsModel.set_setting('printer_usb_vid', self.printer_vid.text())
        SettingsModel.set_setting('printer_usb_pid', self.printer_pid.text())
        SettingsModel.set_setting('printer_serial_port', self.printer_port.text())
        SettingsModel.set_setting('printer_ip', self.printer_ip.text())

        SettingsModel.set_setting('smtp_server', self.smtp_server.text())
        SettingsModel.set_setting('smtp_port', self.smtp_port.text())
        SettingsModel.set_setting('smtp_user', self.smtp_user.text())
        SettingsModel.set_setting('smtp_pass', self.smtp_pass.text())
        
        SettingsModel.set_setting('theme', self.theme_combo.currentText())

        self.accept()
