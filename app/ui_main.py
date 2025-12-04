import sys
from datetime import datetime
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
from app.ui_products import ManageProductsDialog
from app.ui_preview import BillPreviewDialog



from app.ui_customers import ManageCustomersDialog, CustomerDialog

class DebtCustomersDialog(QDialog):
    """Dialog to show customers with pending debt"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Debt Customers")
        self.resize(700, 500)
        self.init_ui()
        self.load_debt_customers()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("💰 Customers with Pending Debt")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        layout.addWidget(title)
        
        # Summary
        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet("padding: 5px; color: #d32f2f;")
        layout.addWidget(self.summary_label)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Customer", "Phone", "Bills", "Total Debt", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 120)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.cellDoubleClicked.connect(self.show_customer_bills)
        layout.addWidget(self.table)
        
        # Info label
        info_label = QLabel("Double-click a customer to view their debt bills")
        info_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(info_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self.load_debt_customers)
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.close)
        btn_layout.addWidget(btn_refresh)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)

    def load_debt_customers(self):
        self.table.setRowCount(0)
        debt_data = BillModel.get_debt_by_customer()
        
        total_debt = sum(d['total_debt'] for d in debt_data)
        self.summary_label.setText(f"Total Outstanding: ₹{total_debt:.2f} from {len(debt_data)} customer(s)")
        
        for row, data in enumerate(debt_data):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(data['customer_name']))
            self.table.setItem(row, 1, QTableWidgetItem(data['customer_phone'] or '-'))
            self.table.setItem(row, 2, QTableWidgetItem(str(data['bill_count'])))
            
            debt_item = QTableWidgetItem(f"₹{data['total_debt']:.2f}")
            debt_item.setForeground(Qt.GlobalColor.red)
            self.table.setItem(row, 3, debt_item)
            
            # Store customer_id in first column
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, data['customer_id'])
            
            # View button
            btn_view = QPushButton("View Bills")
            btn_view.clicked.connect(lambda checked, cid=data['customer_id'], name=data['customer_name']: 
                                    self.show_customer_bills_by_id(cid, name))
            self.table.setCellWidget(row, 4, btn_view)

    def show_customer_bills(self, row, col):
        customer_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        customer_name = self.table.item(row, 0).text()
        self.show_customer_bills_by_id(customer_id, customer_name)

    def show_customer_bills_by_id(self, customer_id, customer_name):
        dialog = CustomerDebtBillsDialog(self, customer_id, customer_name)
        dialog.exec()
        self.load_debt_customers()  # Refresh after closing


class CustomerDebtBillsDialog(QDialog):
    """Dialog to show debt bills for a specific customer"""
    def __init__(self, parent, customer_id, customer_name):
        super().__init__(parent)
        self.customer_id = customer_id
        self.setWindowTitle(f"Debt Bills - {customer_name}")
        self.resize(600, 400)
        self.init_ui()
        self.load_bills()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Bill No.", "Date", "Amount", "Status", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 100)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)
        
        # Total
        self.total_label = QLabel("")
        self.total_label.setStyleSheet("font-weight: bold; font-size: 14px; padding: 10px;")
        layout.addWidget(self.total_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_pay_all = QPushButton("Mark All as Paid")
        btn_pay_all.setStyleSheet("background-color: #4CAF50; color: white;")
        btn_pay_all.clicked.connect(self.mark_all_paid)
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.close)
        btn_layout.addWidget(btn_pay_all)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)

    def load_bills(self):
        self.table.setRowCount(0)
        bills = BillModel.get_customer_debt_bills(self.customer_id)
        
        total = sum(b['grand_total'] for b in bills)
        self.total_label.setText(f"Total Pending: ₹{total:.2f}")
        
        for row, bill in enumerate(bills):
            self.table.insertRow(row)
            
            bill_item = QTableWidgetItem(bill['bill_number'])
            bill_item.setData(Qt.ItemDataRole.UserRole, bill['id'])
            self.table.setItem(row, 0, bill_item)
            
            self.table.setItem(row, 1, QTableWidgetItem(bill['date_time']))
            self.table.setItem(row, 2, QTableWidgetItem(f"₹{bill['grand_total']:.2f}"))
            
            status_item = QTableWidgetItem("UNPAID")
            status_item.setForeground(Qt.GlobalColor.red)
            self.table.setItem(row, 3, status_item)
            
            # Pay button
            btn_pay = QPushButton("Pay")
            btn_pay.setStyleSheet("background-color: #2196F3; color: white;")
            btn_pay.clicked.connect(lambda checked, bid=bill['id']: self.mark_paid(bid))
            self.table.setCellWidget(row, 4, btn_pay)

    def mark_paid(self, bill_id):
        reply = QMessageBox.question(self, "Confirm Payment",
                                    "Mark this bill as paid?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if BillModel.mark_bill_as_paid(bill_id):
                self.load_bills()
            else:
                QMessageBox.warning(self, "Error", "Failed to update bill status")

    def mark_all_paid(self):
        reply = QMessageBox.question(self, "Confirm Payment",
                                    "Mark ALL bills as paid for this customer?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            bills = BillModel.get_customer_debt_bills(self.customer_id)
            for bill in bills:
                BillModel.mark_bill_as_paid(bill['id'])
            self.load_bills()


class PaymentDialog(QDialog):
    def __init__(self, parent=None, total=0.0):
        super().__init__(parent)
        self.main_window = parent
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
        self.method.addItems(["Cash", "UPI", "Card", "Debt"])
        layout.addWidget(self.method)

        btn_pay = QPushButton("Complete Payment")
        btn_pay.clicked.connect(self.complete_payment)
        layout.addWidget(btn_pay)
        
        self.setLayout(layout)

    def complete_payment(self):
        self.payment_method = self.method.currentText()
        
        if self.payment_method == "Debt":
            if not self.main_window.current_customer:
                reply = QMessageBox.question(self, "Customer Required", 
                                           "Debt payment requires a registered customer. Do you want to add one now?",
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                
                if reply == QMessageBox.StandardButton.Yes:
                    dlg = CustomerDialog(self)
                    if dlg.exec():
                        # Update MainWindow with new customer
                        self.main_window.current_customer = {'id': dlg.customer_id, 'name': dlg.customer_name, 'phone': dlg.customer_phone}
                        self.main_window.lbl_cust.setText(f"{dlg.customer_name}")
                        self.main_window.load_customers()
                        self.accept()
                    else:
                        return # User cancelled customer creation
                else:
                    return # User refused to add customer
            else:
                self.accept()
        else:
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
        self.prod_search.returnPressed.connect(self.add_product_to_cart_manual)
        
        self.qty_input = QLineEdit("1")
        self.qty_input.setPlaceholderText("Qty")
        self.qty_input.setFixedWidth(60)
        self.qty_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qty_input.returnPressed.connect(self.add_product_to_cart_manual)
        
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
        
        self.discount_input = QLineEdit("0")
        self.discount_input.setPlaceholderText("%")
        self.discount_input.setFixedWidth(50)
        self.discount_input.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.discount_input.textChanged.connect(self.update_cart_table)
        
        self.lbl_discount_amt = QLabel("0.00")
        self.lbl_discount_amt.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.lbl_grand_total = QLabel("₹0.00")
        self.lbl_grand_total.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lbl_grand_total.setObjectName("lblGrandTotal")
        
        totals_layout.addRow("Subtotal:", self.lbl_subtotal)
        totals_layout.addRow("Tax:", self.lbl_tax)
        totals_layout.addRow("Discount (%):", self.discount_input)
        totals_layout.addRow("Discount Amt:", self.lbl_discount_amt)
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
        recent_header_layout = QHBoxLayout()
        lbl_recent = QLabel("🕒 Recent Bills")
        lbl_recent.setObjectName("sectionHeader")
        
        btn_clear_history = QPushButton("Clear")
        btn_clear_history.setFixedWidth(60)
        btn_clear_history.setToolTip("Clear All Bill History")
        btn_clear_history.clicked.connect(self.clear_bill_history)
        
        recent_header_layout.addWidget(lbl_recent)
        recent_header_layout.addStretch()
        recent_header_layout.addWidget(btn_clear_history)
        
        sidebar_layout.addLayout(recent_header_layout)
        
        self.recent_list = QListWidget()
        sidebar_layout.addWidget(self.recent_list)
        
        # Product Management
        btn_manage_prod = QPushButton("🛠 Manage Products")
        btn_manage_prod.clicked.connect(self.open_product_dialog)
        sidebar_layout.addWidget(btn_manage_prod)

        # Debt Customers
        btn_debt = QPushButton("💰 Debt Customers")
        btn_debt.setStyleSheet("background-color: #ffebee;")
        btn_debt.clicked.connect(self.show_debt_customers)
        sidebar_layout.addWidget(btn_debt)

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
        dlg = ManageCustomersDialog(self)
        if dlg.exec():
            if dlg.selected_customer:
                self.current_customer = dlg.selected_customer
                self.lbl_cust.setText(f"{self.current_customer['name']} ({self.current_customer['phone']})")
            self.load_customers()

    def on_product_select(self, text):
        # Extract name from "Name (Code)"
        name = text.rsplit(' (', 1)[0]
        for p in self.products:
            if p['name'] == name:
                self.add_to_cart(p)
                self.prod_search.clear()
                self.prod_search.setFocus()
                break

    def add_product_to_cart_manual(self):
        text = self.prod_search.text().strip()
        if not text:
            return
            
        # Try to find by code/barcode first (exact match)
        found = False
        for p in self.products:
            if p['code'] == text or p['name'].lower() == text.lower():
                self.add_to_cart(p)
                self.prod_search.clear()
                self.qty_input.setText("1")
                self.prod_search.setFocus()
                found = True
                break
        
        if not found:
            # Try partial match in name or code
            for p in self.products:
                if text.lower() in p['name'].lower() or text.lower() in p['code'].lower():
                    self.add_to_cart(p)
                    self.prod_search.clear()
                    self.qty_input.setText("1")
                    self.prod_search.setFocus()
                    found = True
                    break
        
        if not found:
            # Try completer logic if text matches format "Name (Code)"
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
        
        # Calculate Discount
        try:
            disc_percent = float(self.discount_input.text())
        except ValueError:
            disc_percent = 0.0
            
        discount_amount = (subtotal * disc_percent) / 100
        self.lbl_discount_amt.setText(f"₹{discount_amount:.2f}")
        
        grand_total = subtotal - discount_amount
        self.lbl_grand_total.setText(f"₹{grand_total:.2f}")
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

        grand_total = float(self.lbl_grand_total.text().replace('₹', ''))
        dlg = PaymentDialog(self, grand_total)
        if dlg.exec():
            bill_data = {
                'bill_number': generate_bill_number(),
                'customer_id': self.current_customer['id'] if self.current_customer else None,
                'subtotal': float(self.lbl_subtotal.text().replace('₹', '')),
                'grand_total': grand_total,
                'discount_amount': float(self.lbl_discount_amt.text().replace('₹', '')),
                'payment_method': dlg.payment_method,
                'customer_name': self.current_customer['name'] if self.current_customer else "Walk-in Customer",
                'customer_phone': self.current_customer['phone'] if self.current_customer else "",
                'date_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            try:
                # Save to DB
                BillModel.create_bill(bill_data, self.cart)
                
                # Show Preview & Print
                preview_dlg = BillPreviewDialog(self, bill_data, self.cart, self.printer_manager)
                preview_dlg.exec()

                self.clear_cart()
                self.load_recent_bills()
                # show_info(self, "Success", "Bill processed successfully!") # Preview dialog handles success msg if printed
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

    def show_debt_customers(self):
        """Show dialog with customers who have pending debt"""
        dlg = DebtCustomersDialog(self)
        dlg.exec()

    def clear_bill_history(self):
        reply = QMessageBox.question(self, "Confirm Delete", 
                                   "Are you sure you want to delete ALL bill history? This cannot be undone.",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            BillModel.delete_all_bills()
            self.load_recent_bills()
            show_info(self, "Success", "All bill history cleared.")

    def open_reports(self):
        ReportsDialog(self).exec()

    def open_product_dialog(self):
        ManageProductsDialog(self).exec()
        self.load_products()
