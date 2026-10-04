from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLineEdit, QPushButton, QHeaderView, QMessageBox, QFormLayout, QComboBox,
    QLabel, QSpinBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIntValidator
from app.models import ProductModel
from app.printer import PrinterManager
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
        self.category.setPlaceholderText("e.g. Wooden Toys, STEM, Puzzles")

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

class BarcodePrintDialog(QDialog):
    def __init__(self, parent=None, product_name="Product"):
        super().__init__(parent)
        self.setWindowTitle("Print Labels")
        self.resize(300, 150)
        self.count = 1
        self.init_ui(product_name)

    def init_ui(self, product_name):
        layout = QVBoxLayout()
        
        lbl_info = QLabel(f"Print labels for:\n{product_name}")
        lbl_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_info.setStyleSheet("font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(lbl_info)
        
        form_layout = QHBoxLayout()
        form_layout.addWidget(QLabel("Quantity:"))
        self.spin_qty = QSpinBox()
        self.spin_qty.setRange(1, 100)
        self.spin_qty.setValue(1)
        form_layout.addWidget(self.spin_qty)
        layout.addLayout(form_layout)
        
        btn_layout = QHBoxLayout()
        btn_print = QPushButton("🖨 Print")
        btn_print.clicked.connect(self.confirm_print)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_print)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)

    def confirm_print(self):
        self.count = self.spin_qty.value()
        self.accept()


class ManageProductsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Products")
        self.resize(800, 600)
        self.printer_manager = PrinterManager()
        self.init_ui()
        self.load_products()

    def init_ui(self):
        layout = QVBoxLayout()

        # Top Bar: Search and Add
        top_layout = QHBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("🔍 Search by Name, Code, or Category...")
        self.search_bar.textChanged.connect(self.search_products)
        
        btn_add = QPushButton("+ Add New Product")
        btn_add.clicked.connect(self.add_product)
        
        top_layout.addWidget(self.search_bar)
        top_layout.addWidget(btn_add)
        layout.addLayout(top_layout)

        # Product Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Code", "Unit", "Price", "Category"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.hideColumn(0) # Hide ID column
        layout.addWidget(self.table)

        # Action Buttons
        action_layout = QHBoxLayout()
        btn_edit = QPushButton("✏️ Edit Selected")
        btn_edit.clicked.connect(self.edit_product)
        
        btn_print = QPushButton("🖨 Print Label")
        btn_print.clicked.connect(self.print_label)
        
        btn_delete = QPushButton("🗑️ Delete Selected")
        btn_delete.setObjectName("dangerBtn")
        btn_delete.clicked.connect(self.delete_product)
        
        btn_view_img = QPushButton("🖼 View Image")
        btn_view_img.clicked.connect(self.view_product_image)

        action_layout.addStretch()
        action_layout.addWidget(btn_view_img)
        action_layout.addWidget(btn_print)
        action_layout.addWidget(btn_edit)
        action_layout.addWidget(btn_delete)
        layout.addLayout(action_layout)

        self.table.doubleClicked.connect(self.view_product_image)
        self.setLayout(layout)

    def load_products(self):
        self.products = ProductModel.get_all_products()
        self.update_table(self.products)

    def search_products(self):
        query = self.search_bar.text().strip().lower()
        if not query:
            self.update_table(self.products)
            return
        filtered = [
            p for p in self.products
            if query in p.get('name', '').lower()
            or query in p.get('code', '').lower()
            or query in p.get('category', '').lower()
            or any(query in str(c).lower() for c in p.get('categories', []))
        ]
        self.update_table(filtered)

    def update_table(self, products):
        self.table.setRowCount(len(products))
        for row, p in enumerate(products):
            self.table.setItem(row, 0, QTableWidgetItem(str(p['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(p['name']))
            self.table.setItem(row, 2, QTableWidgetItem(p['code']))
            self.table.setItem(row, 3, QTableWidgetItem(p['base_unit']))
            self.table.setItem(row, 4, QTableWidgetItem(f"{p['price_per_unit']:.2f}"))
            self.table.setItem(row, 5, QTableWidgetItem(p['category']))

    def add_product(self):
        dlg = ProductDialog(self)
        if dlg.exec():
            self.load_products()

    def edit_product(self):
        row = self.table.currentRow()
        if row < 0:
            show_info(self, "Selection", "Please select a product to edit.")
            return
        
        product_id = int(self.table.item(row, 0).text())
        product = next((p for p in self.products if p['id'] == product_id), None)
        
        if product:
            dlg = ProductDialog(self, product)
            if dlg.exec():
                self.load_products()

    def delete_product(self):
        row = self.table.currentRow()
        if row < 0:
            show_info(self, "Selection", "Please select a product to delete.")
            return
        
        product_name = self.table.item(row, 1).text()
        confirm = QMessageBox.question(self, "Confirm Delete", 
                                     f"Are you sure you want to delete '{product_name}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if confirm == QMessageBox.StandardButton.Yes:
            product_id = int(self.table.item(row, 0).text())
            ProductModel.delete_product(product_id)
            self.load_products()

    def print_label(self):
        row = self.table.currentRow()
        if row < 0:
            show_info(self, "Selection", "Please select a product to print label.")
            return

        product_id = int(self.table.item(row, 0).text())
        # Find product in local list
        product = next((p for p in self.products if p['id'] == product_id), None)
        
        if product:
            dlg = BarcodePrintDialog(self, product['name'])
            if dlg.exec():
                try:
                    self.printer_manager.print_barcode_label(product, dlg.count)
                    show_info(self, "Success", f"Sent {dlg.count} labels to printer.")
                except Exception as e:
                    show_error(self, "Printing Error", str(e))

    def view_product_image(self):
        row = self.table.currentRow()
        if row < 0:
            show_info(self, "Selection", "Please select a product to view image.")
            return

        product_id = int(self.table.item(row, 0).text())
        product = next((p for p in self.products if p['id'] == product_id), None)
        if product:
            from app.ui_image_preview import ProductImageDialog
            from app.image_loader import ImageLoader
            img_url = product.get('image_url')
            pix = None
            if img_url:
                loader = ImageLoader.get_instance()
                pix = loader.load_image(img_url)
            dlg = ProductImageDialog(self, product, pix)
            dlg.exec()

