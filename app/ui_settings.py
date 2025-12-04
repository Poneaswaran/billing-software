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
        self.printer_layout = QVBoxLayout()
        
        # Printer Type Selection
        type_group = QGroupBox("Printer Type")
        type_layout = QFormLayout()
        
        self.printer_type = QComboBox()
        self.printer_type.addItems(["Windows Printer", "USB (Direct)", "Serial", "Network", "Dummy"])
        self.printer_type.setCurrentText(SettingsModel.get_setting('printer_type', 'Windows Printer'))
        self.printer_type.currentTextChanged.connect(self.on_printer_type_changed)
        type_layout.addRow("Type:", self.printer_type)
        type_group.setLayout(type_layout)
        self.printer_layout.addWidget(type_group)
        
        # Windows Printer Selection
        self.windows_printer_group = QGroupBox("Windows Printer")
        win_layout = QFormLayout()
        
        win_printer_row = QHBoxLayout()
        self.windows_printer_combo = QComboBox()
        self.windows_printer_combo.setMinimumWidth(250)
        self.refresh_windows_printers()
        self.windows_printer_combo.setCurrentText(SettingsModel.get_setting('windows_printer_name', ''))
        win_printer_row.addWidget(self.windows_printer_combo)
        
        btn_refresh_win = QPushButton("Refresh")
        btn_refresh_win.clicked.connect(self.refresh_windows_printers)
        win_printer_row.addWidget(btn_refresh_win)
        win_layout.addRow("Printer:", win_printer_row)
        
        self.windows_printer_group.setLayout(win_layout)
        self.printer_layout.addWidget(self.windows_printer_group)
        
        # USB Printer Settings
        self.usb_group = QGroupBox("USB Printer (Direct ESC/POS)")
        usb_layout = QFormLayout()
        
        # USB Printer Detection
        usb_detect_row = QHBoxLayout()
        self.usb_printer_combo = QComboBox()
        self.usb_printer_combo.setMinimumWidth(250)
        self.usb_printer_combo.currentIndexChanged.connect(self.on_usb_printer_selected)
        usb_detect_row.addWidget(self.usb_printer_combo)
        
        btn_detect_usb = QPushButton("Detect")
        btn_detect_usb.clicked.connect(self.detect_usb_printers)
        usb_detect_row.addWidget(btn_detect_usb)
        usb_layout.addRow("Detected:", usb_detect_row)
        
        self.printer_vid = QLineEdit(SettingsModel.get_setting('printer_usb_vid', ''))
        self.printer_vid.setPlaceholderText("e.g., 0x0483")
        self.printer_pid = QLineEdit(SettingsModel.get_setting('printer_usb_pid', ''))
        self.printer_pid.setPlaceholderText("e.g., 0x5740")
        usb_layout.addRow("VID (Hex):", self.printer_vid)
        usb_layout.addRow("PID (Hex):", self.printer_pid)
        
        self.usb_group.setLayout(usb_layout)
        self.printer_layout.addWidget(self.usb_group)
        
        # Serial Settings
        self.serial_group = QGroupBox("Serial Port")
        serial_layout = QFormLayout()
        
        serial_row = QHBoxLayout()
        self.printer_port = QComboBox()
        self.printer_port.setEditable(True)
        self.refresh_serial_ports()
        self.printer_port.setCurrentText(SettingsModel.get_setting('printer_serial_port', 'COM1'))
        serial_row.addWidget(self.printer_port)
        
        btn_refresh_serial = QPushButton("Refresh")
        btn_refresh_serial.clicked.connect(self.refresh_serial_ports)
        serial_row.addWidget(btn_refresh_serial)
        serial_layout.addRow("Port:", serial_row)
        
        self.serial_group.setLayout(serial_layout)
        self.printer_layout.addWidget(self.serial_group)
        
        # Network Settings
        self.network_group = QGroupBox("Network Printer")
        network_layout = QFormLayout()
        self.printer_ip = QLineEdit(SettingsModel.get_setting('printer_ip', '192.168.1.100'))
        self.printer_ip.setPlaceholderText("e.g., 192.168.1.100")
        network_layout.addRow("IP Address:", self.printer_ip)
        self.network_group.setLayout(network_layout)
        self.printer_layout.addWidget(self.network_group)
        
        # Paper Size Settings
        paper_group = QGroupBox("Paper Size")
        paper_layout = QFormLayout()
        
        self.paper_size = QComboBox()
        self.paper_size.addItems(["80mm (48 chars)", "58mm (32 chars)", "76mm (42 chars)", "Custom"])
        self.paper_size.setCurrentText(SettingsModel.get_setting('paper_size', '80mm (48 chars)'))
        self.paper_size.currentTextChanged.connect(self.on_paper_size_changed)
        paper_layout.addRow("Paper Width:", self.paper_size)
        
        self.chars_per_line = QSpinBox()
        self.chars_per_line.setRange(20, 80)
        self.chars_per_line.setValue(int(SettingsModel.get_setting('chars_per_line', '48')))
        self.chars_per_line.setSuffix(" characters")
        paper_layout.addRow("Characters/Line:", self.chars_per_line)
        
        self.font_size = QComboBox()
        self.font_size.addItems(["Small", "Normal", "Large"])
        self.font_size.setCurrentText(SettingsModel.get_setting('receipt_font_size', 'Normal'))
        paper_layout.addRow("Font Size:", self.font_size)
        
        self.line_spacing = QComboBox()
        self.line_spacing.addItems(["Compact", "Normal", "Relaxed"])
        self.line_spacing.setCurrentText(SettingsModel.get_setting('line_spacing', 'Normal'))
        paper_layout.addRow("Line Spacing:", self.line_spacing)
        
        paper_group.setLayout(paper_layout)
        self.printer_layout.addWidget(paper_group)
        
        # Initialize paper settings visibility
        self.on_paper_size_changed(self.paper_size.currentText())
        
        # Test Print Button
        btn_test = QPushButton("🖨️ Test Print")
        btn_test.clicked.connect(self.test_print)
        self.printer_layout.addWidget(btn_test)
        
        self.printer_layout.addStretch()
        self.printer_tab.setLayout(self.printer_layout)
        self.tabs.addTab(self.printer_tab, "Printer")
        
        # Initialize visibility
        self.on_printer_type_changed(self.printer_type.currentText())

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
        SettingsModel.set_setting('windows_printer_name', self.windows_printer_combo.currentText())
        SettingsModel.set_setting('printer_usb_vid', self.printer_vid.text())
        SettingsModel.set_setting('printer_usb_pid', self.printer_pid.text())
        SettingsModel.set_setting('printer_serial_port', self.printer_port.currentText())
        SettingsModel.set_setting('printer_ip', self.printer_ip.text())
        
        # Save Paper Size settings
        SettingsModel.set_setting('paper_size', self.paper_size.currentText())
        SettingsModel.set_setting('chars_per_line', str(self.chars_per_line.value()))
        SettingsModel.set_setting('receipt_font_size', self.font_size.currentText())
        SettingsModel.set_setting('line_spacing', self.line_spacing.currentText())

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
    
    def on_paper_size_changed(self, paper_size):
        """Update characters per line based on paper size selection"""
        paper_chars = {
            "80mm (48 chars)": 48,
            "58mm (32 chars)": 32,
            "76mm (42 chars)": 42,
        }
        if paper_size in paper_chars:
            self.chars_per_line.setValue(paper_chars[paper_size])
            self.chars_per_line.setEnabled(False)
        else:  # Custom
            self.chars_per_line.setEnabled(True)
    
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

    # Printer Settings Methods
    def on_printer_type_changed(self, printer_type):
        """Show/hide printer settings based on type"""
        self.windows_printer_group.setVisible(printer_type == "Windows Printer")
        self.usb_group.setVisible(printer_type == "USB (Direct)")
        self.serial_group.setVisible(printer_type == "Serial")
        self.network_group.setVisible(printer_type == "Network")
    
    def refresh_windows_printers(self):
        """Refresh list of Windows printers"""
        self.windows_printer_combo.clear()
        from app.printer import get_windows_printers
        printers = get_windows_printers()
        if printers:
            self.windows_printer_combo.addItems(printers)
        else:
            self.windows_printer_combo.addItem("No printers found")
    
    def detect_usb_printers(self):
        """Detect USB printers"""
        self.usb_printer_combo.clear()
        from app.printer import get_usb_printers
        
        try:
            printers = get_usb_printers()
            if printers:
                for p in printers:
                    label = f"{p['name']} ({p['vid']}:{p['pid']})"
                    if p.get('is_printer'):
                        label = "🖨️ " + label
                    self.usb_printer_combo.addItem(label, p)
                QMessageBox.information(self, "USB Detection", f"Found {len(printers)} USB device(s)")
            else:
                self.usb_printer_combo.addItem("No USB devices found")
                QMessageBox.warning(self, "USB Detection", 
                    "No USB devices found.\n\n"
                    "Make sure:\n"
                    "1. Your printer is connected and powered on\n"
                    "2. libusb is installed (download from libusb.info)\n\n"
                    "Alternatively, use 'Windows Printer' type instead.")
        except Exception as e:
            self.usb_printer_combo.addItem("Detection failed - use Windows Printer")
            QMessageBox.warning(self, "USB Detection Error", 
                f"Could not detect USB devices: {e}\n\n"
                "Try using 'Windows Printer' type instead - it should show your POS80.")
    
    def on_usb_printer_selected(self, index):
        """Fill VID/PID when USB printer is selected"""
        data = self.usb_printer_combo.currentData()
        if data:
            self.printer_vid.setText(data['vid'])
            self.printer_pid.setText(data['pid'])
    
    def refresh_serial_ports(self):
        """Refresh serial ports for printer"""
        self.printer_port.clear()
        try:
            ports = serial.tools.list_ports.comports()
            for port in ports:
                self.printer_port.addItem(f"{port.device}", port.device)
            if not ports:
                self.printer_port.addItem("COM1")
        except Exception:
            self.printer_port.addItems(["COM1", "COM2", "COM3", "COM4"])
    
    def test_print(self):
        """Test print to selected printer"""
        printer_type = self.printer_type.currentText()
        
        if printer_type == "Windows Printer":
            printer_name = self.windows_printer_combo.currentText()
            if not printer_name or printer_name == "No printers found":
                QMessageBox.warning(self, "Error", "Please select a printer first")
                return
            
            # Test using Windows printing
            try:
                import tempfile
                import os
                
                # Create a simple test file
                test_file = os.path.join(tempfile.gettempdir(), "test_print.txt")
                with open(test_file, 'w') as f:
                    f.write("=" * 32 + "\n")
                    f.write("     PRINTER TEST\n")
                    f.write("=" * 32 + "\n")
                    f.write(f"Printer: {printer_name}\n")
                    f.write("If you see this, printing works!\n")
                    f.write("=" * 32 + "\n")
                
                # Print using Windows
                import subprocess
                result = subprocess.run(
                    ['powershell', '-Command', f'Get-Content "{test_file}" | Out-Printer -Name "{printer_name}"'],
                    capture_output=True, text=True, timeout=30
                )
                
                if result.returncode == 0:
                    QMessageBox.information(self, "Success", f"Test sent to {printer_name}!")
                else:
                    QMessageBox.warning(self, "Error", f"Print failed: {result.stderr}")
                    
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Test print failed: {e}")
        
        elif printer_type == "Dummy":
            QMessageBox.information(self, "Dummy Mode", "Dummy mode - no actual printing occurs")
        
        else:
            QMessageBox.information(self, "Test Print", 
                f"To test {printer_type} printer, save settings first and try printing a bill.")
