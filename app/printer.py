import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from escpos.printer import Usb, Serial, Network, Dummy
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

from app.utils.logger import error_logger, transaction_logger
from app.utils.exceptions import PrinterError
from app.models import SettingsModel

class PrinterManager:
    def __init__(self):
        self.printer = None
        self.queue_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'print_queue.json')
        self._load_queue()

    def _load_queue(self):
        if os.path.exists(self.queue_file):
            try:
                with open(self.queue_file, 'r') as f:
                    self.queue = json.load(f)
            except:
                self.queue = []
        else:
            self.queue = []

    def _save_queue(self):
        with open(self.queue_file, 'w') as f:
            json.dump(self.queue, f)

    def connect_printer(self):
        """Attempts to connect to the configured printer."""
        printer_type = SettingsModel.get_setting('printer_type', 'USB')
        try:
            if printer_type == 'USB':
                vid = int(SettingsModel.get_setting('printer_usb_vid', '0'), 16)
                pid = int(SettingsModel.get_setting('printer_usb_pid', '0'), 16)
                if vid and pid:
                    self.printer = Usb(vid, pid)
            elif printer_type == 'Serial':
                port = SettingsModel.get_setting('printer_serial_port', 'COM1')
                self.printer = Serial(port)
            elif printer_type == 'Network':
                ip = SettingsModel.get_setting('printer_ip', '192.168.1.100')
                self.printer = Network(ip)
            else:
                self.printer = Dummy() # Fallback
        except Exception as e:
            error_logger.error(f"Failed to connect to printer: {e}")
            self.printer = Dummy()
            raise PrinterError(f"Could not connect to printer: {e}")

    def print_receipt(self, bill_data, items):
        """Prints the receipt."""
        try:
            if not self.printer:
                self.connect_printer()

            store_name = SettingsModel.get_setting('store_name', 'Thangam Stores')
            store_address = SettingsModel.get_setting('store_address', '123 Main St, City')
            footer_text = SettingsModel.get_setting('receipt_footer', 'Thank you for shopping!')

            self.printer.text(f"{store_name}\n")
            self.printer.text(f"{store_address}\n")
            self.printer.text(f"Date: {bill_data['date_time']}\n")
            self.printer.text(f"Bill No: {bill_data['bill_number']}\n")
            self.printer.text("-" * 32 + "\n")
            self.printer.text(f"{'Item':<16} {'Qty':<5} {'Price':<8}\n")
            self.printer.text("-" * 32 + "\n")

            for item in items:
                name = item['product_name'][:16]
                qty = f"{item['quantity']}{item['unit']}"
                price = f"{item['total']:.2f}"
                self.printer.text(f"{name:<16} {qty:<5} {price:<8}\n")

            self.printer.text("-" * 32 + "\n")
            self.printer.text(f"Subtotal: {bill_data['subtotal']:.2f}\n")
            if bill_data.get('tax_amount'):
                self.printer.text(f"Tax: {bill_data['tax_amount']:.2f}\n")
            if bill_data.get('discount_amount'):
                self.printer.text(f"Discount: -{bill_data['discount_amount']:.2f}\n")
            self.printer.text(f"Total: {bill_data['grand_total']:.2f}\n")
            self.printer.text("-" * 32 + "\n")
            self.printer.text(f"{footer_text}\n")
            self.printer.cut()
            
            transaction_logger.info(f"Printed bill {bill_data['bill_number']}")

        except Exception as e:
            error_logger.error(f"Print failed: {e}")
            self.queue.append({'bill_data': bill_data, 'items': items})
            self._save_queue()
            raise PrinterError("Printing failed. Added to queue.")

    def generate_pdf(self, bill_data, items, filename):
        """Generates a PDF receipt."""
        try:
            c = canvas.Canvas(filename, pagesize=A4)
            width, height = A4
            y = height - 50 * mm

            store_name = SettingsModel.get_setting('store_name', 'Thangam Stores')
            
            c.setFont("Helvetica-Bold", 16)
            c.drawString(20*mm, y, store_name)
            y -= 10*mm
            
            c.setFont("Helvetica", 12)
            c.drawString(20*mm, y, f"Bill No: {bill_data['bill_number']}")
            y -= 10*mm
            c.drawString(20*mm, y, f"Date: {bill_data['date_time']}")
            y -= 20*mm

            # Table Header
            c.drawString(20*mm, y, "Item")
            c.drawString(100*mm, y, "Qty")
            c.drawString(150*mm, y, "Price")
            y -= 10*mm

            for item in items:
                c.drawString(20*mm, y, item['product_name'])
                c.drawString(100*mm, y, f"{item['quantity']} {item['unit']}")
                c.drawString(150*mm, y, f"{item['total']:.2f}")
                y -= 10*mm

            y -= 10*mm
            c.drawString(120*mm, y, f"Total: {bill_data['grand_total']:.2f}")
            
            c.save()
            return True
        except Exception as e:
            error_logger.error(f"PDF generation failed: {e}")
            return False

    def email_receipt(self, bill_data, items, recipient_email):
        """Emails the receipt."""
        smtp_server = SettingsModel.get_setting('smtp_server')
        smtp_port = SettingsModel.get_setting('smtp_port')
        smtp_user = SettingsModel.get_setting('smtp_user')
        smtp_pass = SettingsModel.get_setting('smtp_pass')

        if not all([smtp_server, smtp_port, smtp_user, smtp_pass]):
            raise PrinterError("SMTP settings not configured.")

        try:
            msg = MIMEMultipart()
            msg['From'] = smtp_user
            msg['To'] = recipient_email
            msg['Subject'] = f"Receipt from Thangam Stores - {bill_data['bill_number']}"

            body = f"Thank you for shopping!\n\nBill No: {bill_data['bill_number']}\nTotal: {bill_data['grand_total']:.2f}"
            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(smtp_server, int(smtp_port))
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
            server.quit()
            return True
        except Exception as e:
            error_logger.error(f"Email failed: {e}")
            raise PrinterError(f"Failed to send email: {e}")

    @staticmethod
    def list_usb_printers():
        """Lists connected USB printers (requires implementation specific to OS/Driver, using simple placeholders for now)."""
        # In a real scenario, we might iterate over /dev/usb/lp* or use win32print
        # python-escpos doesn't have a simple 'list all' static method that works universally without probing.
        # We will return a dummy list for UI demonstration if actual detection is hard.
        return [{"name": "Generic USB Printer", "vid": "0x0000", "pid": "0x0000"}]
