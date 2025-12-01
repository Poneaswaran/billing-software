from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLineEdit, QPushButton, QHeaderView, QMessageBox, QFormLayout
)
from PyQt6.QtCore import Qt
from app.models import CustomerModel
from app.ui_error_handler import show_error, show_info

class CustomerDialog(QDialog):
    def __init__(self, parent=None, customer=None):
        super().__init__(parent)
        self.setWindowTitle("Add/Edit Customer")
        self.customer = customer
        self.customer_id = None
        self.customer_name = None
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout()
        self.name = QLineEdit(self.customer['name'] if self.customer else "")
        self.phone = QLineEdit(self.customer['phone'] if self.customer else "")
        self.address = QLineEdit(self.customer['address'] if self.customer else "")
        
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
        
        if self.customer:
            success = CustomerModel.update_customer(self.customer['id'], self.name.text(), self.phone.text(), self.address.text())
            if success:
                self.customer_id = self.customer['id']
                self.customer_name = self.name.text()
                self.accept()
            else:
                show_error(self, "Error", "Could not update customer.")
        else:
            cid = CustomerModel.add_customer(self.name.text(), self.phone.text(), self.address.text())
            if cid:
                self.customer_id = cid
                self.customer_name = self.name.text()
                self.customer_phone = self.phone.text()
                self.accept()
            else:
                show_error(self, "Error", "Could not add customer. Phone might be duplicate.")

class ManageCustomersDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Customers")
        self.resize(800, 600)
        self.selected_customer = None # To return if needed
        self.init_ui()
        self.load_customers()

    def init_ui(self):
        layout = QVBoxLayout()

        # Top Bar: Search and Add
        top_layout = QHBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("🔍 Search by Name or Phone...")
        self.search_bar.textChanged.connect(self.search_customers)
        
        btn_add = QPushButton("+ Add New Customer")
        btn_add.clicked.connect(self.add_customer)
        
        top_layout.addWidget(self.search_bar)
        top_layout.addWidget(btn_add)
        layout.addLayout(top_layout)

        # Customer Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Phone", "Address"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.hideColumn(0) # Hide ID column
        self.table.doubleClicked.connect(self.select_and_close) # Double click to select
        layout.addWidget(self.table)

        # Action Buttons
        action_layout = QHBoxLayout()
        btn_select = QPushButton("Select (Enter)")
        btn_select.clicked.connect(self.select_and_close)
        
        btn_edit = QPushButton("Edit Selected")
        btn_edit.clicked.connect(self.edit_customer)
        
        btn_delete = QPushButton("Delete Selected")
        btn_delete.setObjectName("dangerBtn")
        btn_delete.clicked.connect(self.delete_customer)
        
        action_layout.addWidget(btn_select)
        action_layout.addStretch()
        action_layout.addWidget(btn_edit)
        action_layout.addWidget(btn_delete)
        layout.addLayout(action_layout)

        self.setLayout(layout)

    def load_customers(self):
        self.customers = CustomerModel.get_all_customers()
        self.update_table(self.customers)

    def search_customers(self):
        query = self.search_bar.text().lower()
        filtered = [c for c in self.customers if query in c['name'].lower() or query in c['phone']]
        self.update_table(filtered)

    def update_table(self, customers):
        self.table.setRowCount(len(customers))
        for row, c in enumerate(customers):
            self.table.setItem(row, 0, QTableWidgetItem(str(c['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(c['name']))
            self.table.setItem(row, 2, QTableWidgetItem(c['phone']))
            self.table.setItem(row, 3, QTableWidgetItem(c['address']))

    def add_customer(self):
        dlg = CustomerDialog(self)
        if dlg.exec():
            self.load_customers()
            # If added, maybe select it automatically?
            # For now just reload

    def edit_customer(self):
        row = self.table.currentRow()
        if row < 0:
            show_info(self, "Selection", "Please select a customer to edit.")
            return
        
        customer_id = int(self.table.item(row, 0).text())
        customer = next((c for c in self.customers if c['id'] == customer_id), None)
        
        if customer:
            dlg = CustomerDialog(self, customer)
            if dlg.exec():
                self.load_customers()

    def delete_customer(self):
        row = self.table.currentRow()
        if row < 0:
            show_info(self, "Selection", "Please select a customer to delete.")
            return
        
        customer_name = self.table.item(row, 1).text()
        confirm = QMessageBox.question(self, "Confirm Delete", 
                                     f"Are you sure you want to delete '{customer_name}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if confirm == QMessageBox.StandardButton.Yes:
            customer_id = int(self.table.item(row, 0).text())
            CustomerModel.delete_customer(customer_id)
            self.load_customers()

    def select_and_close(self):
        row = self.table.currentRow()
        if row >= 0:
            customer_id = int(self.table.item(row, 0).text())
            self.selected_customer = next((c for c in self.customers if c['id'] == customer_id), None)
            self.accept()
