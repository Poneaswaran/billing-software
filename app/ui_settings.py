from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, 
    QComboBox, QTabWidget, QWidget, QLabel, QHBoxLayout, QSpinBox,
    QCheckBox, QGroupBox, QMessageBox
)
from PyQt6.QtCore import Qt
from app.models import SettingsModel
from app.printer import PrinterManager
import serial.tools.list_ports

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

        # Barcode Scanner Settings
        self.scanner_tab = QWidget()
        self.scanner_layout = QVBoxLayout()
        
        # Scanner Type Group
        scanner_type_group = QGroupBox("Scanner Type")
        scanner_type_layout = QFormLayout()
        
        self.scanner_type = QComboBox()
        self.scanner_type.addItems(["USB HID (Keyboard Mode)", "Serial COM Port", "Keyboard Wedge"])
        self.scanner_type.setCurrentText(SettingsModel.get_setting('scanner_type', 'USB HID (Keyboard Mode)'))
        self.scanner_type.currentTextChanged.connect(self.on_scanner_type_changed)
        scanner_type_layout.addRow("Scanner Type:", self.scanner_type)
        
        scanner_type_group.setLayout(scanner_type_layout)
        self.scanner_layout.addWidget(scanner_type_group)
        
        # Serial Port Settings Group
        self.serial_group = QGroupBox("Serial Port Settings")
        serial_layout = QFormLayout()
        
        # COM Port selection with refresh button
        com_port_layout = QHBoxLayout()
        self.scanner_com_port = QComboBox()
        self.scanner_com_port.setMinimumWidth(200)
        self.refresh_com_ports()
        self.scanner_com_port.setCurrentText(SettingsModel.get_setting('scanner_com_port', ''))
        com_port_layout.addWidget(self.scanner_com_port)
        
        self.refresh_ports_btn = QPushButton("Refresh")
        self.refresh_ports_btn.clicked.connect(self.refresh_com_ports)
        com_port_layout.addWidget(self.refresh_ports_btn)
        com_port_layout.addStretch()
        
        serial_layout.addRow("COM Port:", com_port_layout)
        
        self.scanner_baud_rate = QComboBox()
        self.scanner_baud_rate.addItems(["1200", "2400", "4800", "9600", "19200", "38400", "57600", "115200"])
        self.scanner_baud_rate.setCurrentText(SettingsModel.get_setting('scanner_baud_rate', '9600'))
        serial_layout.addRow("Baud Rate:", self.scanner_baud_rate)
        
        self.serial_group.setLayout(serial_layout)
        self.scanner_layout.addWidget(self.serial_group)
        
        # Scanner Behavior Group
        behavior_group = QGroupBox("Scanner Behavior")
        behavior_layout = QFormLayout()
        
        self.scanner_prefix = QLineEdit(SettingsModel.get_setting('scanner_prefix', ''))
        self.scanner_prefix.setPlaceholderText("Characters before barcode (optional)")
        behavior_layout.addRow("Barcode Prefix:", self.scanner_prefix)
        
        self.scanner_suffix = QComboBox()
        self.scanner_suffix.addItems(["Enter (\\r)", "Newline (\\n)", "Tab (\\t)", "None"])
        self.scanner_suffix.setCurrentText(SettingsModel.get_setting('scanner_suffix', 'Enter (\\r)'))
        behavior_layout.addRow("Barcode Suffix:", self.scanner_suffix)
        
        self.scanner_timeout = QSpinBox()
        self.scanner_timeout.setRange(50, 1000)
        self.scanner_timeout.setSuffix(" ms")
        self.scanner_timeout.setValue(int(SettingsModel.get_setting('scanner_timeout', '100')))
        behavior_layout.addRow("Scan Timeout:", self.scanner_timeout)
        
        behavior_group.setLayout(behavior_layout)
        self.scanner_layout.addWidget(behavior_group)
        
        # Options Group
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()
        
        self.scanner_auto_focus = QCheckBox("Auto-focus barcode field on scan")
        self.scanner_auto_focus.setChecked(SettingsModel.get_setting('scanner_auto_focus', 'true').lower() == 'true')
        options_layout.addWidget(self.scanner_auto_focus)
        
        self.scanner_beep = QCheckBox("Play sound on successful scan")
        self.scanner_beep.setChecked(SettingsModel.get_setting('scanner_beep', 'true').lower() == 'true')
        options_layout.addWidget(self.scanner_beep)
        
        self.scanner_auto_search = QCheckBox("Auto-search product after scan")
        self.scanner_auto_search.setChecked(SettingsModel.get_setting('scanner_auto_search', 'true').lower() == 'true')
        options_layout.addWidget(self.scanner_auto_search)
        
        options_group.setLayout(options_layout)
        self.scanner_layout.addWidget(options_group)
        
        # Test Scanner Button
        test_layout = QHBoxLayout()
        self.test_scanner_btn = QPushButton("Test Scanner")
        self.test_scanner_btn.clicked.connect(self.test_scanner)
        test_layout.addWidget(self.test_scanner_btn)
        test_layout.addStretch()
        self.scanner_layout.addLayout(test_layout)
        
        self.scanner_layout.addStretch()
        self.scanner_tab.setLayout(self.scanner_layout)
        self.tabs.addTab(self.scanner_tab, "Barcode Scanner")
        
        # Initialize serial group visibility
        self.on_scanner_type_changed(self.scanner_type.currentText())

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

        # Save Barcode Scanner settings
        SettingsModel.set_setting('scanner_type', self.scanner_type.currentText())
        SettingsModel.set_setting('scanner_com_port', self.scanner_com_port.currentText())
        SettingsModel.set_setting('scanner_baud_rate', self.scanner_baud_rate.currentText())
        SettingsModel.set_setting('scanner_prefix', self.scanner_prefix.text())
        SettingsModel.set_setting('scanner_suffix', self.scanner_suffix.currentText())
        SettingsModel.set_setting('scanner_timeout', str(self.scanner_timeout.value()))
        SettingsModel.set_setting('scanner_auto_focus', str(self.scanner_auto_focus.isChecked()).lower())
        SettingsModel.set_setting('scanner_beep', str(self.scanner_beep.isChecked()).lower())
        SettingsModel.set_setting('scanner_auto_search', str(self.scanner_auto_search.isChecked()).lower())

        self.accept()

    def on_scanner_type_changed(self, scanner_type):
        """Enable/disable serial settings based on scanner type"""
        is_serial = scanner_type == "Serial COM Port"
        self.serial_group.setEnabled(is_serial)
    
    def refresh_com_ports(self):
        """Refresh the list of available COM ports"""
        self.scanner_com_port.clear()
        try:
            ports = serial.tools.list_ports.comports()
            for port in ports:
                self.scanner_com_port.addItem(f"{port.device} - {port.description}", port.device)
            if not ports:
                self.scanner_com_port.addItem("No COM ports found")
        except Exception:
            self.scanner_com_port.addItem("Could not detect COM ports")
    
    def test_scanner(self):
        """Open a dialog to test the barcode scanner"""
        test_dialog = QDialog(self)
        test_dialog.setWindowTitle("Test Barcode Scanner")
        test_dialog.resize(400, 150)
        
        layout = QVBoxLayout()
        
        label = QLabel("Scan a barcode to test the scanner:")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        
        test_input = QLineEdit()
        test_input.setPlaceholderText("Scanned barcode will appear here...")
        test_input.setStyleSheet("font-size: 16px; padding: 10px;")
        layout.addWidget(test_input)
        
        result_label = QLabel("")
        result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(result_label)
        
        def on_scan():
            if test_input.text():
                result_label.setText(f"✓ Scanner working! Scanned: {test_input.text()}")
                result_label.setStyleSheet("color: green; font-weight: bold;")
        
        test_input.returnPressed.connect(on_scan)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(test_dialog.accept)
        layout.addWidget(close_btn)
        
        test_dialog.setLayout(layout)
        test_input.setFocus()
        test_dialog.exec()
