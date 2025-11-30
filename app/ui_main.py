import sys
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
    QTableWidgetItem, QLineEdit, QLabel, QPushButton, QComboBox, 
    QDialog, QFormLayout, QCompleter, QHeaderView, QSplitter, 
    QListWidget, QGridLayout, QFrame, QMessageBox, QApplication
)
from PyQt6.QtCore import Qt, QStringListModel, QTimer
from PyQt6.QtGui import QAction, QKeySequence, QFont

from app.models import ProductModel, CustomerModel, BillModel, SettingsModel
from app.utils.helpers import generate_bill_number, convert_unit
from app.printer import PrinterManager
from app.ui_settings import SettingsDialog
from app.ui_reports import ReportsDialog
from app.ui_error_handler import show_error, show_info
from app.ui_error_handler import show_error, show_info

class ProductDialog(QDialog):
    def __init__(self, parent=None, product=None):
        super().__init__(parent)
        self.setWindowTitle("Add/Edit Product")
        self.product = product
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout()
        self.name = QLineEdit(self.product['name'] if self.product else "")
        self.code = QLineEdit(self.product['code'] if self.product else "")
        self.unit = QComboBox()
        self.unit.addItems(["kg", "g", "litre", "ml", "pc"])
        if self.product: self.unit.setCurrentText(self.product['base_unit'])
        
        self.price = QLineEdit(str(self.product['price_per_unit']) if self.product else "")
        self.category = QLineEdit(self.product['category'] if self.product else "General")

        layout.addRow("Name:", self.name)
        layout.addRow("Code:", self.code)
        layout.addRow("Base Unit:", self.unit)
        layout.addRow("Price:", self.price)
        layout.addRow("Category:", self.category)

        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self.save_product)
        layout.addRow(btn_save)
        self.setLayout(layout)

    def save_product(self):
        try:
            price = float(self.price.text())
            if self.product:
                ProductModel.update_product(self.product['id'], self.name.text(), self.code.text(), 
                                          self.unit.currentText(), price, self.category.text())
            else:
                ProductModel.add_product(self.name.text(), self.code.text(), 
                                       self.unit.currentText(), price, self.category.text())
            self.accept()
        except ValueError:
            show_error(self, "Input Error", "Price must be a number.")

class CustomerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Customer")
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout()
        self.name = QLineEdit()
        self.phone = QLineEdit()
        self.address = QLineEdit()
        
        layout.addRow("Name:", self.name)
        layout.addRow("Phone:", self.phone)
        layout.addRow("Address:", self.address)
        
        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self.save_customer)
        layout.addRow(btn_save)
        self.setLayout(layout)

    def save_customer(self):
        if not self.name.text() or not self.phone.text():
            show_error(self, "Error", "Name and Phone are required.")
            return
        
        cid = CustomerModel.add_customer(self.name.text(), self.phone.text(), self.address.text())
        if cid:
            self.customer_id = cid
            self.customer_name = self.name.text()
            self.accept()
        else:
            show_error(self, "Error", "Could not add customer. Phone might be duplicate.")

class PaymentDialog(QDialog):
    def __init__(self, parent=None, total=0.0):
        super().__init__(parent)
        self.setWindowTitle("Payment")
        self.total = total
        self.payment_method = "Cash"
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        lbl_total = QLabel(f"Total to Pay: ₹{self.total:.2f}")
        lbl_total.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(lbl_total)

        self.method = QComboBox()
        self.method.addItems(["Cash", "UPI", "Card"])
        layout.addWidget(self.method)

        btn_pay = QPushButton("Complete Payment")
        btn_pay.clicked.connect(self.complete_payment)
        layout.addWidget(btn_pay)
        
        self.setLayout(layout)

    def complete_payment(self):
        self.payment_method = self.method.currentText()
        self.accept()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Thangam Stores Billing")
        self.resize(1200, 800)
        self.printer_manager = PrinterManager()
        self.cart = []
        self.current_customer = None
        self.init_ui()
        self.load_products()
        self.load_customers()
        self.load_recent_bills()

    def init_ui(self):
        # ... (menu code)
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.open_settings)
        file_menu.addAction(settings_action)

        reports_action = QAction("Reports", self)
        reports_action.triggered.connect(self.open_reports)
        file_menu.addAction(reports_action)
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Left Side: Billing
        billing_layout = QVBoxLayout()
        billing_layout.setSpacing(15)
        
        # Customer Section
        cust_group = QWidget()
        cust_layout = QHBoxLayout(cust_group)
        cust_layout.setContentsMargins(0, 0, 0, 0)
        
        self.cust_search = QLineEdit()
        self.cust_search.setPlaceholderText("🔍 Search Customer (Name/Phone)...")
        self.cust_completer = QCompleter()
        self.cust_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.cust_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.cust_completer.activated.connect(self.on_customer_select)
        self.cust_search.setCompleter(self.cust_completer)
        self.cust_search.returnPressed.connect(self.search_customer)
        btn_add_cust = QPushButton("+ New")
        btn_add_cust.setToolTip("Add New Customer")
        btn_add_cust.clicked.connect(self.add_customer)
        self.lbl_cust = QLabel("Walk-in Customer")
        self.lbl_cust.setStyleSheet("font-weight: bold; color: #555;")
        
        cust_layout.addWidget(self.cust_search, 2)
        cust_layout.addWidget(btn_add_cust)
        cust_layout.addWidget(self.lbl_cust, 1)
        billing_layout.addWidget(cust_group)

        # Product Search
        prod_group = QWidget()
        prod_layout = QHBoxLayout(prod_group)
        prod_layout.setContentsMargins(0, 0, 0, 0)

        self.prod_search = QLineEdit()
        self.prod_search.setPlaceholderText("📦 Scan Barcode or Search Product...")
        self.prod_search.setMinimumHeight(40)
        self.prod_completer = QCompleter()
        self.prod_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.prod_completer.activated.connect(self.on_product_select)
        self.prod_search.setCompleter(self.prod_completer)
        
        self.qty_input = QLineEdit("1")
        self.qty_input.setPlaceholderText("Qty")
        self.qty_input.setFixedWidth(60)
        self.qty_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        btn_add_prod = QPushButton("Add Item")
        btn_add_prod.clicked.connect(self.add_product_to_cart_manual)

        prod_layout.addWidget(self.prod_search, 4)
        prod_layout.addWidget(self.qty_input)
        prod_layout.addWidget(btn_add_prod)
        billing_layout.addWidget(prod_group)

        # Cart Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Product", "Qty", "Unit", "Price", "Total"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.cellChanged.connect(self.on_cart_item_changed)
        billing_layout.addWidget(self.table)

        # Totals
        totals_frame = QFrame()
        totals_frame.setObjectName("totalsFrame")
        totals_layout = QFormLayout(totals_frame)
        totals_layout.setContentsMargins(20, 20, 20, 20)
        
        self.lbl_subtotal = QLabel("0.00")
        self.lbl_subtotal.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lbl_tax = QLabel("0.00")
        self.lbl_tax.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lbl_discount = QLabel("0.00")
        self.lbl_discount.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.lbl_grand_total = QLabel("₹0.00")
        self.lbl_grand_total.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lbl_grand_total.setObjectName("lblGrandTotal")
        
        totals_layout.addRow("Subtotal:", self.lbl_subtotal)
        totals_layout.addRow("Tax:", self.lbl_tax)
        totals_layout.addRow("Discount:", self.lbl_discount)
        totals_layout.addRow("Grand Total:", self.lbl_grand_total)
        billing_layout.addWidget(totals_frame)

        # Actions
        actions_layout = QHBoxLayout()
        btn_clear = QPushButton("Clear Bill")
        btn_clear.setObjectName("dangerBtn")
        btn_clear.setMinimumHeight(50)
        btn_clear.clicked.connect(self.clear_cart)
        
        btn_print = QPushButton("Complete & Print (F12)")
        btn_print.setObjectName("primaryBtn")
        btn_print.setMinimumHeight(50)
        btn_print.clicked.connect(self.process_bill)
        
        actions_layout.addWidget(btn_clear)
        actions_layout.addWidget(btn_print, 2)
        billing_layout.addLayout(actions_layout)

        # Right Side: Sidebar (Recent Bills & Quick Products)
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setSpacing(15)
        
        # Quick Products
        lbl_quick = QLabel("⚡ Quick Products")
        lbl_quick.setObjectName("sectionHeader")
        sidebar_layout.addWidget(lbl_quick)
        
        self.quick_grid = QGridLayout()
        # Placeholder for quick buttons logic
        sidebar_layout.addLayout(self.quick_grid)

        # Recent Bills
        lbl_recent = QLabel("🕒 Recent Bills")
        lbl_recent.setObjectName("sectionHeader")
        sidebar_layout.addWidget(lbl_recent)
        
        self.recent_list = QListWidget()
        sidebar_layout.addWidget(self.recent_list)
        
        # Product Management
        btn_manage_prod = QPushButton("🛠 Manage Products")
        btn_manage_prod.clicked.connect(self.open_product_dialog)
        sidebar_layout.addWidget(btn_manage_prod)

        # Settings
        btn_settings = QPushButton("⚙ Settings")
        btn_settings.clicked.connect(self.open_settings)
        sidebar_layout.addWidget(btn_settings)

        # Combine Layouts
        splitter = QSplitter(Qt.Orientation.Horizontal)
        left_widget = QWidget()
        left_widget.setLayout(billing_layout)
        right_widget = QWidget()
        right_widget.setLayout(sidebar_layout)
        
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(splitter)

        # Shortcuts
        QAction("Print", self, shortcut=QKeySequence("F12"), triggered=self.process_bill)

    def load_products(self):
        self.products = ProductModel.get_all_products()
        names = [f"{p['name']} ({p['code']})" for p in self.products]
        model = QStringListModel(names)
        self.prod_completer.setModel(model)

    def load_customers(self):
        self.customers = CustomerModel.get_all_customers()
        names = [f"{c['name']} ({c['phone']})" for c in self.customers]
        model = QStringListModel(names)
        self.cust_completer.setModel(model)

    def load_recent_bills(self):
        self.recent_list.clear()
        bills = BillModel.get_recent_bills()
        for b in bills:
            self.recent_list.addItem(f"{b['bill_number']} - ₹{b['grand_total']:.2f}")

    def search_customer(self):
        query = self.cust_search.text()
        # Try to find in loaded customers first
        for c in self.customers:
            if query.lower() in c['name'].lower() or query in c['phone']:
                self.current_customer = c
                self.lbl_cust.setText(f"{c['name']} ({c['phone']})")
                self.cust_search.clear()
                return

        customers = CustomerModel.search_customer(query)
        if customers:
            # Simple selection: take first
            c = customers[0]
            self.current_customer = c
            self.lbl_cust.setText(f"{c['name']} ({c['phone']})")
            self.cust_search.clear()
        else:
            show_info(self, "Not Found", "Customer not found.")

    def on_customer_select(self, text):
        # Extract phone from "Name (Phone)"
        if '(' in text and text.endswith(')'):
            phone = text.split('(')[-1][:-1]
            for c in self.customers:
                if c['phone'] == phone:
                    self.current_customer = c
                    self.lbl_cust.setText(f"{c['name']} ({c['phone']})")
                    self.cust_search.clear()
                    break

    def add_customer(self):
        dlg = CustomerDialog(self)
        if dlg.exec():
            self.current_customer = {'id': dlg.customer_id, 'name': dlg.customer_name}
            self.lbl_cust.setText(f"{dlg.customer_name}")
            self.load_customers()

    def on_product_select(self, text):
        # Extract name from "Name (Code)"
        name = text.rsplit(' (', 1)[0]
        for p in self.products:
            if p['name'] == name:
                self.add_to_cart(p)
                self.prod_search.clear()
                break

    def add_product_to_cart_manual(self):
        text = self.prod_search.text()
        # Try to find by code first
        found = False
        for p in self.products:
            if p['code'] == text or p['name'] == text:
                self.add_to_cart(p)
                self.prod_search.clear()
                found = True
                break
        if not found:
            # Try completer logic if text matches
            self.on_product_select(text)

    def add_to_cart(self, product):
        try:
            qty = float(self.qty_input.text())
        except ValueError:
            qty = 1.0
        
        total = qty * product['price_per_unit']
        
        self.cart.append({
            'product_id': product['id'],
            'product_name': product['name'],
            'quantity': qty,
            'unit': product['base_unit'],
            'price': product['price_per_unit'],
            'total': total
        })
        self.update_cart_table()

    def update_cart_table(self):
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.cart))
        subtotal = 0
        for row, item in enumerate(self.cart):
            # Product Name (Read-only)
            name_item = QTableWidgetItem(item['product_name'])
            name_item.setFlags(name_item.flags() ^ Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, name_item)
            
            # Qty (Editable)
            self.table.setItem(row, 1, QTableWidgetItem(str(item['quantity'])))
            
            # Unit (Editable - ideally ComboBox but text for now)
            self.table.setItem(row, 2, QTableWidgetItem(item['unit']))
            
            # Price (Editable)
            self.table.setItem(row, 3, QTableWidgetItem(f"{item['price']:.2f}"))
            
            # Total (Read-only)
            total_item = QTableWidgetItem(f"₹{item['total']:.2f}")
            total_item.setFlags(total_item.flags() ^ Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 4, total_item)
            
            subtotal += item['total']
        
        self.lbl_subtotal.setText(f"₹{subtotal:.2f}")
        self.lbl_grand_total.setText(f"₹{subtotal:.2f}")
        self.table.blockSignals(False)

    def on_cart_item_changed(self, row, column):
        try:
            item = self.cart[row]
            if column == 1: # Qty
                item['quantity'] = float(self.table.item(row, column).text())
            elif column == 2: # Unit
                item['unit'] = self.table.item(row, column).text()
            elif column == 3: # Price
                # Remove currency symbol if present
                text = self.table.item(row, column).text().replace('₹', '')
                item['price'] = float(text)
            
            # Recalculate total
            item['total'] = item['quantity'] * item['price']
            self.update_cart_table()
        except ValueError:
            pass # Ignore invalid input

    def clear_cart(self):
        self.cart = []
        self.current_customer = None
        self.lbl_cust.setText("Walk-in Customer")
        self.update_cart_table()

    def process_bill(self):
        if not self.cart:
            show_error(self, "Empty Cart", "Add items to cart first.")
            return

        grand_total = float(self.lbl_grand_total.text())
        dlg = PaymentDialog(self, grand_total)
        if dlg.exec():
            bill_data = {
                'bill_number': generate_bill_number(),
                'customer_id': self.current_customer['id'] if self.current_customer else None,
                'subtotal': float(self.lbl_subtotal.text()),
                'grand_total': grand_total,
                'payment_method': dlg.payment_method,
                'date_time': "Now" # Placeholder, DB handles actual time
            }
            
            try:
                # Save to DB
                BillModel.create_bill(bill_data, self.cart)
                
                # Print
                try:
                    self.printer_manager.print_receipt(bill_data, self.cart)
                except Exception as e:
                    show_error(self, "Printing Error", f"Bill saved but print failed: {e}")

                self.clear_cart()
                self.load_recent_bills()
                show_info(self, "Success", "Bill processed successfully!")
            except Exception as e:
                show_error(self, "Error", f"Failed to process bill: {e}")

    def open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec():
            # Reload Theme
            from app.models import SettingsModel
            from app.ui_styles import get_theme_style
            theme = SettingsModel.get_setting('theme', 'Light')
            QApplication.instance().setStyleSheet(get_theme_style(theme))

    def open_reports(self):
        ReportsDialog(self).exec()

    def open_product_dialog(self):
        ProductDialog(self).exec()
        self.load_products()
