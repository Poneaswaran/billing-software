import sys
import os
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
    QTableWidgetItem, QLineEdit, QLabel, QPushButton, QComboBox, 
    QDialog, QFormLayout, QCompleter, QHeaderView, QSplitter, 
    QListWidget, QGridLayout, QFrame, QMessageBox, QApplication,
    QSystemTrayIcon, QMenu, QStyle
)
from PyQt6.QtCore import Qt, QStringListModel, QTimer
from PyQt6.QtGui import QAction, QKeySequence, QFont, QIcon

from app.models import ProductModel, CustomerModel, BillModel, SettingsModel
from app.utils.helpers import generate_bill_number, convert_unit
from app.printer import PrinterManager
from app.ui_settings import SettingsDialog
from app.ui_reports import ReportsDialog
from app.ui_error_handler import show_error, show_info
from app.ui_products import ManageProductsDialog
from app.ui_preview import BillPreviewDialog
from app.ui_image_preview import ProductImageDialog
from app.ui_search_dropdown import ProductSearchLineEdit
from app.sync import CloudConnectionChecker, DailyCatalogSyncWorker, ToyPopSyncClient

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
        self.summary_label.setStyleSheet("padding: 5px; color: #e74c3c; font-weight: bold;")
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
        info_label.setStyleSheet("color: #8892a0; font-style: italic;")
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

from app.ui_dashboard import DashboardWidget

class HeldBillsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Held Bills")
        self.resize(600, 400)
        self.selected_bill = None
        self.init_ui()
        self.load_bills()

    def init_ui(self):
        layout = QVBoxLayout()
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Bill No", "Customer", "Time", "Amount"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.cellDoubleClicked.connect(self.resume_bill)
        layout.addWidget(self.table)

        btn_resume = QPushButton("Resume Selected")
        btn_resume.clicked.connect(self.resume_bill)
        layout.addWidget(btn_resume)
        
        self.setLayout(layout)

    def load_bills(self):
        self.bills = BillModel.get_held_bills()
        self.table.setRowCount(len(self.bills))
        for row, bill in enumerate(self.bills):
            self.table.setItem(row, 0, QTableWidgetItem(bill['bill_number']))
            self.table.setItem(row, 1, QTableWidgetItem(bill['customer_name'] or "Walk-in"))
            self.table.setItem(row, 2, QTableWidgetItem(bill['date_time']))
            self.table.setItem(row, 3, QTableWidgetItem(f"₹{bill['grand_total']:.2f}"))
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, bill['id'])

    def resume_bill(self):
        row = self.table.currentRow()
        if row >= 0:
            bill_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            self.selected_bill = next((b for b in self.bills if b['id'] == bill_id), None)
            self.accept()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Thangam Stores Billing")
        self.resize(1200, 800)
        self.printer_manager = PrinterManager()
        self.cart = []
        self.current_customer = None
        self.toypop_connected = False
        self.conn_checker = None
        self.daily_sync_worker = None
        self.force_quit = False
        self.minimize_to_tray_on_close = SettingsModel.get_setting('minimize_to_tray', 'true').lower() == 'true'
        self.tray_icon = None
        self.single_instance_server = None
        self._notified_tray_minimize = False
        self.init_ui()
        self.init_tray_icon()
        self.load_products()
        self.load_customers()
        self.load_recent_bills()
        self.check_toypop_connection()

        # Keyboard Shortcuts
        self.shortcut_f1 = QAction("Focus Search", self)
        self.shortcut_f1.setShortcut("F1")
        self.shortcut_f1.triggered.connect(self.focus_search)
        self.addAction(self.shortcut_f1)

        self.shortcut_f2 = QAction("Focus Qty", self)
        self.shortcut_f2.setShortcut("F2")
        self.shortcut_f2.triggered.connect(self.qty_input.setFocus)
        self.addAction(self.shortcut_f2)

        self.shortcut_f3 = QAction("Focus Discount", self)
        self.shortcut_f3.setShortcut("F3")
        self.shortcut_f3.triggered.connect(self.discount_input.setFocus)
        self.addAction(self.shortcut_f3)

    def init_ui(self):
        from PyQt6.QtWidgets import QTabWidget
        
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
        exit_action.triggered.connect(self.force_quit_app)
        file_menu.addAction(exit_action)

        # ToyPop Cloud Sync Menu
        cloud_menu = menubar.addMenu("☁️ ToyPop Cloud")
        
        sync_all_action = QAction("Sync All Now (F5)", self)
        sync_all_action.setShortcut("F5")
        sync_all_action.triggered.connect(self.trigger_full_cloud_sync)
        cloud_menu.addAction(sync_all_action)
        
        sync_cat_action = QAction("Download Products Catalog", self)
        sync_cat_action.triggered.connect(self.trigger_catalog_sync)
        cloud_menu.addAction(sync_cat_action)
        
        upload_bills_action = QAction("Upload Pending Offline Bills", self)
        upload_bills_action.triggered.connect(self.trigger_bills_sync)
        cloud_menu.addAction(upload_bills_action)
        
        cloud_menu.addSeparator()
        test_cloud_action = QAction("Test Connection", self)
        test_cloud_action.triggered.connect(self.test_cloud_handshake)
        cloud_menu.addAction(test_cloud_action)

        # Tabs
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Tab 1: Billing
        self.billing_tab = QWidget()
        self.init_billing_tab()
        self.tabs.addTab(self.billing_tab, "Billing")

        # Tab 2: Dashboard
        self.dashboard_tab = DashboardWidget()
        self.tabs.addTab(self.dashboard_tab, "Dashboard")

        # Status Bar with Cloud Connection Badge
        status_bar = self.statusBar()
        self.status_cloud_lbl = QLabel("⚪ ToyPop: Checking...")
        self.status_cloud_lbl.setObjectName("statusCloudLbl")
        self.update_cloud_status_style(False)
        status_bar.addPermanentWidget(self.status_cloud_lbl)

    def update_cloud_status_style(self, connected: bool, store_name: str = ""):
        if not hasattr(self, 'status_cloud_lbl'):
            return
        from app.models import SettingsModel
        theme = SettingsModel.get_setting('theme', 'Light')
        is_dark = (theme == 'Dark')
        if connected:
            color = "#4cd137" if is_dark else "#2e7d32"
            text = f"🟢 ToyPop: Connected ({store_name})" if store_name else "🟢 ToyPop: Connected"
        else:
            color = "#8892a0" if is_dark else "#777777"
            text = "⚪ ToyPop: Offline"
        self.status_cloud_lbl.setText(text)
        self.status_cloud_lbl.setStyleSheet(f"padding: 2px 10px; font-weight: bold; color: {color}; font-size: 11px;")

    def init_billing_tab(self):
        main_layout = QHBoxLayout(self.billing_tab)
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
        self.cust_search.setPlaceholderText("🔍 Search Customer (Name/Phone)... [F1]")
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
        self.lbl_cust.setObjectName("lblCust")
        
        cust_layout.addWidget(self.cust_search, 2)
        cust_layout.addWidget(btn_add_cust)
        cust_layout.addWidget(self.lbl_cust, 1)
        billing_layout.addWidget(cust_group)

        # Product Search
        prod_group = QWidget()
        prod_layout = QHBoxLayout(prod_group)
        prod_layout.setContentsMargins(0, 0, 0, 0)

        self.prod_search = ProductSearchLineEdit(self)
        self.prod_search.product_selected.connect(self.on_product_dropdown_selected)
        self.prod_search.returnPressed.connect(self.add_product_to_cart_manual)
        
        self.qty_input = QLineEdit("1")
        self.qty_input.setPlaceholderText("Qty [F2]")
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
        self.table.itemClicked.connect(self.on_cart_item_clicked)
        self.table.itemDoubleClicked.connect(self.on_cart_item_double_clicked)
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
        self.discount_input.setPlaceholderText("% [F3]")
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
        btn_hold = QPushButton("Hold Bill")
        btn_hold.setObjectName("holdBtn")
        btn_hold.setMinimumHeight(50)
        btn_hold.clicked.connect(self.hold_bill)

        btn_clear = QPushButton("Clear Bill")
        btn_clear.setObjectName("dangerBtn")
        btn_clear.setMinimumHeight(50)
        btn_clear.clicked.connect(self.clear_cart)
        
        btn_print = QPushButton("Complete & Print (F12)")
        btn_print.setObjectName("primaryBtn")
        btn_print.setMinimumHeight(50)
        btn_print.clicked.connect(self.process_bill)
        
        actions_layout.addWidget(btn_hold)
        actions_layout.addWidget(btn_clear)
        actions_layout.addWidget(btn_print, 2)
        billing_layout.addLayout(actions_layout)

        # Right Side: Sidebar (Recent Bills & Quick Products)
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setSpacing(15)
        
        # Resume Bill Button
        self.btn_resume = QPushButton("📄 Resume Held Bill")
        self.btn_resume.setObjectName("resumeBtn")
        self.btn_resume.clicked.connect(self.resume_held_bill)
        sidebar_layout.addWidget(self.btn_resume)

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
        btn_debt.setObjectName("debtBtn")
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

    def focus_search(self):
        self.cust_search.setFocus()
        self.cust_search.selectAll()

    def hold_bill(self):
        if not self.cart:
            show_error(self, "Empty Cart", "Cannot hold an empty bill.")
            return

        grand_total = float(self.lbl_grand_total.text().replace('₹', ''))
        bill_data = {
            'bill_number': generate_bill_number(),
            'customer_id': self.current_customer['id'] if self.current_customer else None,
            'subtotal': float(self.lbl_subtotal.text().replace('₹', '')),
            'grand_total': grand_total,
            'discount_amount': float(self.lbl_discount_amt.text().replace('₹', '')),
            'date_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        try:
            BillModel.hold_bill(bill_data, self.cart)
            show_info(self, "Bill Held", "Bill has been put on hold.")
            self.clear_cart()
        except Exception as e:
            show_error(self, "Error", f"Failed to hold bill: {e}")

    def resume_held_bill(self):
        dlg = HeldBillsDialog(self)
        if dlg.exec() and dlg.selected_bill:
            bill = dlg.selected_bill
            
            # Load Customer
            if bill['customer_id']:
                # Would be better to fetch customer details, but for now we might have them in result if we joined
                # Re-fetching just to be safe or simple assignment if name/phone is enough
                self.current_customer = {
                    'id': bill['customer_id'],
                    'name': bill.get('customer_name', 'Unknown'),
                    'phone': bill.get('customer_phone', '')
                }
                self.lbl_cust.setText(f"{self.current_customer['name']} ({self.current_customer['phone']})")
                self.cust_search.clear()
            else:
                self.current_customer = None
                self.lbl_cust.setText("Walk-in Customer")
                
            # Load Items
            items = BillModel.get_bill_items(bill['id'])
            self.cart = items
            
            # Delete the held bill to avoid dupes logic (as per plan)
            BillModel.delete_bill(bill['id'])
            
            self.update_cart_table()
            show_info(self, "Resumed", "Bill resumed successfully.")

    def load_products(self):
        self.products = ProductModel.get_all_products()
        if hasattr(self, 'prod_search'):
            self.prod_search.set_products(self.products)

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
                # Auto focus product search after resolving customer
                self.prod_search.setFocus()
                return

        customers = CustomerModel.search_customer(query)
        if customers:
            # Simple selection: take first
            c = customers[0]
            self.current_customer = c
            self.lbl_cust.setText(f"{c['name']} ({c['phone']})")
            self.cust_search.clear()
            self.prod_search.setFocus()
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
                    self.prod_search.setFocus()
                    break

    def add_customer(self):
        dlg = ManageCustomersDialog(self)
        if dlg.exec():
            if dlg.selected_customer:
                self.current_customer = dlg.selected_customer
                self.lbl_cust.setText(f"{self.current_customer['name']} ({self.current_customer['phone']})")
            self.load_customers()

    def on_product_dropdown_selected(self, product):
        """Called when a product is clicked/selected in the search dropdown popup."""
        if not product:
            return
        self.add_to_cart(product)
        self.qty_input.setText("1")
        self.prod_search.clear()
        self.prod_search.setFocus()

    def add_product_to_cart_manual(self):
        text = self.prod_search.text().strip()
        if not text:
            return
            
        # Try to find by code/barcode first (exact match)
        found = False
        for p in self.products:
            if p['code'].lower() == text.lower() or p['name'].lower() == text.lower():
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

    def on_cart_item_clicked(self, item):
        pass

    def on_cart_item_double_clicked(self, item):
        """Opens high-resolution image dialog when double-clicking a cart item."""
        row = item.row()
        if row < len(self.cart):
            cart_item = self.cart[row]
            prod_id = cart_item.get('product_id')
            p = next((x for x in self.products if x['id'] == prod_id), None)
            if p and p.get('image_url') and self.toypop_connected:
                from app.ui_image_preview import ProductImageDialog
                from app.image_loader import ImageLoader
                loader = ImageLoader.get_instance()
                pix = loader.load_image(p['image_url'])
                dlg = ProductImageDialog(self, p, pix)
                dlg.exec()

    def check_toypop_connection(self):
        """Asynchronously checks if ToyPop Cloud is connected."""
        try:
            self.conn_checker = CloudConnectionChecker(parent=self)
            self.conn_checker.status_checked.connect(self.on_cloud_status_updated)
            self.conn_checker.start()
        except Exception:
            self.on_cloud_status_updated(False, {})

    def on_cloud_status_updated(self, connected: bool, data: dict):
        self.toypop_connected = connected
        if hasattr(self, 'prod_search'):
            self.prod_search.set_toypop_connected(connected)
        store_name = data.get("store", {}).get("name", "ToyPop Cloud") if connected else ""
        self.update_cloud_status_style(connected, store_name)
        if connected:
            self.trigger_daily_or_first_time_sync()

    def trigger_daily_or_first_time_sync(self):
        """Automatically downloads catalog on first time setup or performs daily sync when cloud connected."""
        try:
            self.daily_sync_worker = DailyCatalogSyncWorker(parent=self)
            self.daily_sync_worker.sync_started.connect(self.on_daily_sync_started)
            self.daily_sync_worker.sync_completed.connect(self.on_daily_sync_completed)
            self.daily_sync_worker.start()
        except Exception as e:
            print(f"[Sync] Daily sync trigger note: {e}")

    def on_daily_sync_started(self, message: str):
        self.statusBar().showMessage(f"☁️ {message}", 6000)

    def on_daily_sync_completed(self, success: bool, res: dict):
        if success:
            self.load_products()
            is_first = res.get("is_first_time", False)
            synced = res.get("synced", 0)
            created = res.get("created", 0)
            if is_first:
                msg = f"✓ Initial setup complete: {created} products downloaded from ToyPop Cloud!"
            else:
                msg = f"✓ Daily catalog update complete: {synced} updated, {created} new products"
            self.statusBar().showMessage(msg, 6000)

    def init_tray_icon(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        self.tray_icon = QSystemTrayIcon(self)
        
        # Load icon
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "assets", "icon.ico")
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
        else:
            icon = self.windowIcon()
            if icon.isNull():
                icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
                
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("ToyPop POS & Billing (Ready - Instant Launch)")
        
        tray_menu = QMenu()
        open_act = QAction("🏪 Open Billing Screen", self)
        open_act.triggered.connect(self.show_and_activate)
        tray_menu.addAction(open_act)
        
        sync_act = QAction("☁️ Sync Cloud Catalog", self)
        sync_act.triggered.connect(self.trigger_full_cloud_sync)
        tray_menu.addAction(sync_act)
        
        settings_act = QAction("⚙️ Settings", self)
        settings_act.triggered.connect(self.open_settings)
        tray_menu.addAction(settings_act)
        
        tray_menu.addSeparator()
        exit_act = QAction("❌ Exit ToyPop Billing", self)
        exit_act.triggered.connect(self.force_quit_app)
        tray_menu.addAction(exit_act)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        
        show_tray = SettingsModel.get_setting('show_tray_icon', 'true').lower() == 'true'
        if show_tray:
            self.tray_icon.show()

    def on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show_and_activate()

    def show_and_activate(self):
        from app.single_instance import force_activate_window
        force_activate_window(self)

    def force_quit_app(self):
        self.force_quit = True
        self.close()
        QApplication.quit()

    def closeEvent(self, event):
        if not getattr(self, 'force_quit', False) and getattr(self, 'minimize_to_tray_on_close', True):
            event.ignore()
            self.hide()
            if not getattr(self, '_notified_tray_minimize', False):
                if hasattr(self, 'tray_icon') and self.tray_icon and self.tray_icon.isVisible():
                    self.tray_icon.showMessage(
                        "ToyPop Billing",
                        "Application minimized to background. Click desktop shortcut or tray icon to open instantly!",
                        QSystemTrayIcon.MessageIcon.Information,
                        2500
                    )
                    self._notified_tray_minimize = True
            return

        # Full shutdown cleanup
        if hasattr(self, 'tray_icon') and self.tray_icon:
            self.tray_icon.hide()
        if hasattr(self, 'single_instance_server') and self.single_instance_server:
            self.single_instance_server.close()
        if hasattr(self, 'conn_checker') and self.conn_checker and self.conn_checker.isRunning():
            self.conn_checker.wait(1000)
        if hasattr(self, 'daily_sync_worker') and self.daily_sync_worker and self.daily_sync_worker.isRunning():
            self.daily_sync_worker.wait(1000)
        super().closeEvent(event)

    def add_to_cart(self, product):
        try:
            qty = float(self.qty_input.text())
        except ValueError:
            qty = 1.0
        
        # Check if product already exists in cart
        for item in self.cart:
            if item['product_id'] == product['id']:
                item['quantity'] += qty
                item['total'] = item['quantity'] * item['price']
                self.update_cart_table()
                return

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

                # Trigger non-blocking cloud sync if connection available
                try:
                    from app.sync import ToyPopSyncClient
                    client = ToyPopSyncClient()
                    client.sync_pending_bills()
                except Exception:
                    pass  # Offline immunity: bill is safely persisted in local SQLite
            except Exception as e:
                show_error(self, "Error", f"Failed to process bill: {e}")

    def open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec():
            # Reload Theme
            from app.models import SettingsModel
            from app.ui_styles import apply_theme_to_app
            theme = SettingsModel.get_setting('theme', 'Light')
            touch_mode = SettingsModel.get_setting('touch_mode', 'false').lower() == 'true'
            apply_theme_to_app(QApplication.instance(), theme, touch_mode)
            if hasattr(self, 'prod_search'):
                self.prod_search.apply_theme(theme)
            self.update_cloud_status_style(self.toypop_connected)

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

    def test_cloud_handshake(self):
        from app.sync import ToyPopSyncClient
        client = ToyPopSyncClient()
        res = client.bootstrap()
        if res.get("success"):
            store = res["data"].get("store", {})
            self.check_toypop_connection()
            QMessageBox.information(
                self,
                "Cloud Connected",
                f"Connected to ToyPop Cloud!\n\nStore: {store.get('name')}\nGSTIN: {store.get('gstin')}\nServer Time: {res['data'].get('serverTime')}"
            )
        else:
            self.check_toypop_connection()
            QMessageBox.warning(
                self,
                "Connection Failed",
                f"Could not connect to ToyPop Cloud:\n{res.get('error')}"
            )

    def trigger_catalog_sync(self):
        from app.sync import ToyPopSyncClient
        client = ToyPopSyncClient()
        self.statusBar().showMessage("Downloading updated product catalog from ToyPop Cloud...")
        res = client.sync_catalog(limit=250)
        if res.get("success"):
            self.load_products()
            self.check_toypop_connection()
            self.statusBar().showMessage(f"✓ Catalog updated: {res.get('synced')} updated, {res.get('created')} new products", 5000)
            QMessageBox.information(
                self,
                "Catalog Synced",
                f"Product catalog updated from cloud!\n\nUpdated: {res.get('synced')}\nNew Products: {res.get('created')}\nTotal in batch: {res.get('total')}"
            )
        else:
            self.statusBar().showMessage("✗ Catalog sync failed", 5000)
            QMessageBox.warning(self, "Sync Error", f"Catalog sync failed:\n{res.get('error')}")

    def trigger_bills_sync(self):
        from app.sync import ToyPopSyncClient
        client = ToyPopSyncClient()
        self.statusBar().showMessage("Uploading pending bills to ToyPop Cloud...")
        res = client.sync_pending_bills()
        if res.get("success"):
            synced = res.get("synced_bills", 0)
            self.statusBar().showMessage(f"✓ Uploaded {synced} bills to cloud", 5000)
            QMessageBox.information(
                self,
                "Bills Synchronized",
                f"Offline retail bills uploaded to cloud!\n\nUploaded: {synced}\nRemaining: {res.get('pending', 0)}"
            )
        else:
            self.statusBar().showMessage("✗ Bill upload encountered errors", 5000)
            errs = "\n".join(res.get("errors", ["Unknown error"]))
            QMessageBox.warning(self, "Upload Issue", f"Some bills failed to sync:\n{errs}")

    def trigger_full_cloud_sync(self):
        from app.sync import ToyPopSyncClient
        client = ToyPopSyncClient()
        self.statusBar().showMessage("Performing full ToyPop Cloud synchronization...")
        res = client.full_sync()
        if res.get("success"):
            self.load_products()
            cat = res.get("catalog", {})
            bills = res.get("bills", {})
            self.statusBar().showMessage(f"✓ Full sync completed: {cat.get('synced', 0)} prods updated, {bills.get('synced_bills', 0)} bills uploaded", 6000)
            QMessageBox.information(
                self,
                "Sync Complete",
                f"Full synchronization completed!\n\nCatalog: {cat.get('synced', 0)} updated, {cat.get('created', 0)} new\nBills Uploaded: {bills.get('synced_bills', 0)}"
            )
        else:
            self.statusBar().showMessage("✗ Synchronization error", 5000)
            QMessageBox.warning(self, "Sync Warning", "One or more sync steps encountered issues. Check settings and network.")
