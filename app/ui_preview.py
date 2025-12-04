from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QLabel, QFileDialog
)
from PyQt6.QtCore import Qt
from app.models import SettingsModel
from app.ui_error_handler import show_error, show_info
import os

class BillPreviewDialog(QDialog):
    def __init__(self, parent, bill_data, items, printer_manager):
        super().__init__(parent)
        self.setWindowTitle("Bill Preview")
        self.resize(400, 600)
        self.bill_data = bill_data
        self.items = items
        self.printer_manager = printer_manager
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Get paper settings
        paper_size = SettingsModel.get_setting('paper_size', '80mm (48 chars)')
        chars_per_line = int(SettingsModel.get_setting('chars_per_line', '48'))
        
        # Calculate preview width based on paper size
        paper_widths = {
            "80mm (48 chars)": 380,
            "58mm (32 chars)": 280,
            "76mm (42 chars)": 340,
        }
        preview_width = paper_widths.get(paper_size, int(chars_per_line * 8))

        # Preview Area
        lbl_preview = QLabel(f"Receipt Preview ({paper_size})")
        lbl_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_preview)

        self.preview_area = QTextEdit()
        self.preview_area.setReadOnly(True)
        self.preview_area.setFixedWidth(preview_width) 
        self.preview_area.setStyleSheet("background-color: white; color: black; font-family: 'Courier New'; font-size: 11px;")
        
        self.generate_text_preview()
        
        # Center the preview area
        h_layout = QHBoxLayout()
        h_layout.addStretch()
        h_layout.addWidget(self.preview_area)
        h_layout.addStretch()
        layout.addLayout(h_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.reject)
        
        btn_pdf = QPushButton("📄 Export PDF")
        btn_pdf.clicked.connect(self.export_pdf)
        
        btn_print = QPushButton("🖨 Print")
        btn_print.setObjectName("primaryBtn")
        btn_print.clicked.connect(self.print_bill)
        
        btn_layout.addWidget(btn_close)
        btn_layout.addWidget(btn_pdf)
        btn_layout.addWidget(btn_print)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def generate_text_preview(self):
        """Generate a text preview that matches the actual print output"""
        store_name = SettingsModel.get_setting('store_name', 'Thangam Stores')
        store_address = SettingsModel.get_setting('store_address', '')
        store_phone = SettingsModel.get_setting('store_phone', '')
        footer_text = SettingsModel.get_setting('receipt_footer', 'Thank you for shopping!')
        
        # Get paper settings
        WIDTH = int(SettingsModel.get_setting('chars_per_line', '48'))
        line_spacing = SettingsModel.get_setting('line_spacing', 'Normal')
        
        # Calculate column widths based on paper width
        if WIDTH >= 48:
            item_col = 24
            qty_col = 8
            amt_col = 14
        elif WIDTH >= 42:
            item_col = 20
            qty_col = 8
            amt_col = 12
        else:  # 32 or less (58mm paper)
            item_col = 14
            qty_col = 6
            amt_col = 10
        
        # Spacing between sections
        spacing = "" if line_spacing == "Compact" else "\n" if line_spacing == "Relaxed" else ""
        
        # Build receipt text (same as printer output)
        lines = []
        lines.append("=" * WIDTH)
        lines.append(f"{store_name[:WIDTH]:^{WIDTH}}")
        if store_address:
            if len(store_address) > WIDTH:
                lines.append(store_address[:WIDTH])
                if len(store_address) > WIDTH:
                    lines.append(f"{store_address[WIDTH:WIDTH*2]:^{WIDTH}}")
            else:
                lines.append(f"{store_address:^{WIDTH}}")
        if store_phone:
            lines.append(f"{'Ph: ' + store_phone:^{WIDTH}}")
        lines.append("=" * WIDTH)
        if spacing:
            lines.append(spacing)
        lines.append(f"Bill No: {self.bill_data['bill_number']}")
        lines.append(f"Date: {self.bill_data['date_time']}")
        lines.append(f"Customer: {self.bill_data.get('customer_name', 'Walk-in')[:WIDTH-10]}")
        if self.bill_data.get('customer_phone'):
            lines.append(f"Phone: {self.bill_data['customer_phone']}")
        if spacing:
            lines.append(spacing)
        lines.append("-" * WIDTH)
        lines.append(f"{'ITEM':<{item_col}} {'QTY':^{qty_col}} {'AMT':>{amt_col}}")
        lines.append("-" * WIDTH)
        
        for item in self.items:
            name = item['product_name'][:item_col]
            qty = f"{item['quantity']}{item['unit']}"[:qty_col]
            amt = f"{item['total']:.2f}"[:amt_col]
            lines.append(f"{name:<{item_col}} {qty:^{qty_col}} {amt:>{amt_col}}")
        
        lines.append("-" * WIDTH)
        if spacing:
            lines.append(spacing)
        
        # Calculate label and amount column widths
        label_col = WIDTH - amt_col - 2
        
        lines.append(f"{'Subtotal':<{label_col}} Rs.{self.bill_data['subtotal']:>{amt_col-3}.2f}")
        if self.bill_data.get('tax_amount') and self.bill_data['tax_amount'] > 0:
            lines.append(f"{'Tax':<{label_col}} Rs.{self.bill_data['tax_amount']:>{amt_col-3}.2f}")
        if self.bill_data.get('discount_amount') and self.bill_data['discount_amount'] > 0:
            lines.append(f"{'Discount':<{label_col}} -{self.bill_data['discount_amount']:>{amt_col-2}.2f}")
        if spacing:
            lines.append(spacing)
        lines.append("=" * WIDTH)
        lines.append(f"{'TOTAL':<{label_col}} Rs.{self.bill_data['grand_total']:>{amt_col-3}.2f}")
        lines.append("=" * WIDTH)
        if spacing:
            lines.append(spacing)
        lines.append(f"{'Pay: ' + self.bill_data.get('payment_method', 'Cash'):^{WIDTH}}")
        if spacing:
            lines.append(spacing)
        lines.append(f"{footer_text[:WIDTH]:^{WIDTH}}")
        lines.append(f"{'*** THANK YOU ***':^{WIDTH}}")
        
        receipt_text = "\n".join(lines)
        
        # Display as plain text with monospace font
        self.preview_area.setPlainText(receipt_text)

    def print_bill(self):
        try:
            self.printer_manager.print_receipt(self.bill_data, self.items)
            show_info(self, "Success", "Print command sent!")
            self.accept()
        except Exception as e:
            show_error(self, "Printing Error", f"Print failed: {e}")

    def export_pdf(self):
        """Export the bill as a PDF file"""
        # Default filename
        default_name = f"Bill_{self.bill_data['bill_number'].replace('/', '_')}.pdf"
        
        # Get save location from user
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Bill as PDF",
            default_name,
            "PDF Files (*.pdf)"
        )
        
        if not file_path:
            return  # User cancelled
        
        try:
            from reportlab.lib.pagesizes import mm
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import mm
            
            store_name = SettingsModel.get_setting('store_name', 'Thangam Stores')
            store_address = SettingsModel.get_setting('store_address', '')
            store_phone = SettingsModel.get_setting('store_phone', '')
            footer_text = SettingsModel.get_setting('receipt_footer', 'Thank you for shopping!')
            
            # 80mm width receipt paper (80mm x variable height)
            page_width = 80 * mm
            page_height = 200 * mm  # Will adjust based on content
            
            # Calculate height needed
            num_items = len(self.items)
            estimated_height = (180 + (num_items * 15)) * mm / 3
            page_height = max(estimated_height, 150 * mm)
            
            c = canvas.Canvas(file_path, pagesize=(page_width, page_height))
            
            # Starting Y position (from top)
            y = page_height - 10 * mm
            left_margin = 5 * mm
            right_margin = page_width - 5 * mm
            center = page_width / 2
            
            # Store Header
            c.setFont("Helvetica-Bold", 14)
            c.drawCentredString(center, y, store_name)
            y -= 5 * mm
            
            if store_address:
                c.setFont("Helvetica", 8)
                c.drawCentredString(center, y, store_address)
                y -= 4 * mm
            
            if store_phone:
                c.setFont("Helvetica", 8)
                c.drawCentredString(center, y, f"Phone: {store_phone}")
                y -= 4 * mm
            
            # Separator
            y -= 2 * mm
            c.setLineWidth(0.5)
            c.line(left_margin, y, right_margin, y)
            y -= 5 * mm
            
            # Bill Info
            c.setFont("Helvetica", 9)
            c.drawString(left_margin, y, f"Bill No: {self.bill_data['bill_number']}")
            y -= 4 * mm
            c.drawString(left_margin, y, f"Date: {self.bill_data['date_time']}")
            y -= 4 * mm
            c.drawString(left_margin, y, f"Customer: {self.bill_data.get('customer_name', 'Walk-in')}")
            y -= 4 * mm
            if self.bill_data.get('customer_phone'):
                c.drawString(left_margin, y, f"Phone: {self.bill_data['customer_phone']}")
                y -= 4 * mm
            
            # Items Header
            y -= 2 * mm
            c.line(left_margin, y, right_margin, y)
            y -= 4 * mm
            
            c.setFont("Helvetica-Bold", 8)
            c.drawString(left_margin, y, "Item")
            c.drawCentredString(center, y, "Qty")
            c.drawRightString(right_margin, y, "Amount")
            y -= 3 * mm
            c.line(left_margin, y, right_margin, y)
            y -= 4 * mm
            
            # Items
            c.setFont("Helvetica", 8)
            for item in self.items:
                name = item['product_name'][:20]
                qty = f"{item['quantity']} {item['unit']}"
                amt = f"Rs.{item['total']:.2f}"
                
                c.drawString(left_margin, y, name)
                c.drawCentredString(center, y, qty)
                c.drawRightString(right_margin, y, amt)
                y -= 4 * mm
            
            # Totals
            y -= 2 * mm
            c.line(left_margin, y, right_margin, y)
            y -= 5 * mm
            
            c.setFont("Helvetica", 9)
            c.drawString(left_margin, y, "Subtotal:")
            c.drawRightString(right_margin, y, f"Rs.{self.bill_data['subtotal']:.2f}")
            y -= 4 * mm
            
            if self.bill_data.get('tax_amount') and self.bill_data['tax_amount'] > 0:
                c.drawString(left_margin, y, "Tax:")
                c.drawRightString(right_margin, y, f"Rs.{self.bill_data['tax_amount']:.2f}")
                y -= 4 * mm
            
            if self.bill_data.get('discount_amount') and self.bill_data['discount_amount'] > 0:
                c.drawString(left_margin, y, "Discount:")
                c.drawRightString(right_margin, y, f"-Rs.{self.bill_data['discount_amount']:.2f}")
                y -= 4 * mm
            
            # Grand Total
            y -= 2 * mm
            c.setLineWidth(1)
            c.line(left_margin, y, right_margin, y)
            y -= 5 * mm
            
            c.setFont("Helvetica-Bold", 11)
            c.drawString(left_margin, y, "TOTAL:")
            c.drawRightString(right_margin, y, f"Rs.{self.bill_data['grand_total']:.2f}")
            y -= 4 * mm
            c.line(left_margin, y, right_margin, y)
            y -= 6 * mm
            
            # Payment Method
            c.setFont("Helvetica", 9)
            c.drawCentredString(center, y, f"Payment: {self.bill_data.get('payment_method', 'Cash')}")
            y -= 6 * mm
            
            # Footer
            c.setFont("Helvetica", 8)
            c.drawCentredString(center, y, footer_text)
            y -= 5 * mm
            c.drawCentredString(center, y, "*** THANK YOU ***")
            
            c.save()
            
            show_info(self, "Success", f"PDF saved to:\n{file_path}")
            
            # Ask if user wants to open the PDF
            from PyQt6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self, "Open PDF?", 
                "Do you want to open the PDF file?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                os.startfile(file_path)
                
        except Exception as e:
            show_error(self, "PDF Error", f"Failed to create PDF: {e}")
