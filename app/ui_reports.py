from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, 
    QDateEdit, QPushButton, QLabel, QHeaderView
)
from PyQt6.QtCore import QDate, Qt
from app.db import get_db_connection

from app.ui_styles import TOTAL_LABEL_STYLE

class ReportsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sales Reports")
        self.resize(900, 700)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # Filters
        filter_layout = QHBoxLayout()
        self.start_date = QDateEdit(QDate.currentDate())
        self.start_date.setCalendarPopup(True)
        self.end_date = QDateEdit(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        
        btn_generate = QPushButton("Generate Report")
        btn_generate.setObjectName("primaryBtn")
        btn_generate.clicked.connect(self.generate_report)
        
        filter_layout.addWidget(QLabel("Start Date:"))
        filter_layout.addWidget(self.start_date)
        filter_layout.addWidget(QLabel("End Date:"))
        filter_layout.addWidget(self.end_date)
        filter_layout.addWidget(btn_generate)
        layout.addLayout(filter_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Date", "Bill No", "Customer", "Payment", "Total"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        # Summary
        self.lbl_total_sales = QLabel("Total Sales: ₹0.00")
        self.lbl_total_sales.setStyleSheet(TOTAL_LABEL_STYLE)
        self.lbl_total_sales.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.lbl_total_sales)

        self.setLayout(layout)

    def generate_report(self):
        start = self.start_date.date().toString("yyyy-MM-dd")
        end = self.end_date.date().toString("yyyy-MM-dd")
        
        # Add time to cover the full end day
        start_ts = f"{start} 00:00:00"
        end_ts = f"{end} 23:59:59"

        conn = get_db_connection()
        bills = conn.execute('''
            SELECT b.*, c.name as customer_name 
            FROM bills b 
            LEFT JOIN customers c ON b.customer_id = c.id
            WHERE date_time BETWEEN ? AND ?
        ''', (start_ts, end_ts)).fetchall()
        conn.close()

        self.table.setRowCount(len(bills))
        total_sales = 0

        for row, bill in enumerate(bills):
            self.table.setItem(row, 0, QTableWidgetItem(bill['date_time']))
            self.table.setItem(row, 1, QTableWidgetItem(bill['bill_number']))
            self.table.setItem(row, 2, QTableWidgetItem(bill['customer_name'] or "Walk-in"))
            self.table.setItem(row, 3, QTableWidgetItem(bill['payment_method']))
            self.table.setItem(row, 4, QTableWidgetItem(f"₹{bill['grand_total']:.2f}"))
            total_sales += bill['grand_total']

        self.lbl_total_sales.setText(f"Total Sales: ₹{total_sales:.2f}")
