import os
import json
import smtplib
import subprocess
import tempfile
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


def get_windows_printers():
    """Get list of Windows printers"""
    printers = []
    try:
        import win32print
        for printer in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS):
            printers.append(printer[2])
    except ImportError:
        try:
            result = subprocess.run(
                ['powershell', '-Command', 'Get-Printer | Select-Object -ExpandProperty Name'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                printers = [p.strip() for p in result.stdout.strip().split('\n') if p.strip()]
        except Exception:
            pass
    return printers


def get_usb_printers():
    """Detect USB printers"""
    printers = []
    try:
        import usb.core
        import usb.util
        devices = usb.core.find(find_all=True)
        for device in devices:
            try:
                manufacturer = ""
                product = ""
                try:
                    manufacturer = usb.util.get_string(device, device.iManufacturer) or ""
                except:
                    pass
                try:
                    product = usb.util.get_string(device, device.iProduct) or ""
                except:
                    pass
                vid = hex(device.idVendor)
                pid = hex(device.idProduct)
                is_printer = False
                name = f"{manufacturer} {product}".strip()
                if device.bDeviceClass == 7:
                    is_printer = True
                for cfg in device:
                    for intf in cfg:
                        if intf.bInterfaceClass == 7:
                            is_printer = True
                            break
                name_lower = name.lower()
                if any(kw in name_lower for kw in ['printer', 'pos', 'receipt', 'thermal', 'escpos', 'epson']):
                    is_printer = True
                if is_printer or name:
                    printers.append({
                        'name': name if name else f"USB Device {vid}:{pid}",
                        'vid': vid,
                        'pid': pid,
                        'is_printer': is_printer
                    })
            except Exception:
                continue
    except Exception as e:
        error_logger.error(f"USB detection error: {e}")
    return printers


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
        printer_type = SettingsModel.get_setting('printer_type', 'Windows Printer')
        try:
            if printer_type == 'USB (Direct)':
                vid = int(SettingsModel.get_setting('printer_usb_vid', '0'), 16)
                pid = int(SettingsModel.get_setting('printer_usb_pid', '0'), 16)
                if vid and pid:
                    self.printer = Usb(vid, pid)
                else:
                    self.printer = Dummy()
            elif printer_type == 'Serial':
                port = SettingsModel.get_setting('printer_serial_port', 'COM1')
                self.printer = Serial(port)
            elif printer_type == 'Network':
                ip = SettingsModel.get_setting('printer_ip', '192.168.1.100')
                self.printer = Network(ip)
            elif printer_type == 'Windows Printer':
                self.printer = None  # Will use Windows printing
            else:
                self.printer = Dummy()
        except Exception as e:
            error_logger.error(f"Failed to connect to printer: {e}")
            self.printer = Dummy()

    def print_receipt(self, bill_data, items):
        """Prints the receipt."""
        printer_type = SettingsModel.get_setting('printer_type', 'Windows Printer')
        
        # Use Windows printing for Windows Printer type
        if printer_type == 'Windows Printer':
            return self.print_receipt_windows(bill_data, items)
        
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
            self.printer.text(f"Customer: {bill_data.get('customer_name', 'Walk-in')}\n")
            if bill_data.get('customer_phone'):
                self.printer.text(f"Phone: {bill_data['customer_phone']}\n")
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

    def print_receipt_windows(self, bill_data, items):
        """Print receipt using Windows printer with ESC/POS auto-cut"""
        printer_name = SettingsModel.get_setting('windows_printer_name', '')
        if not printer_name:
            raise PrinterError("No Windows printer configured")
        
        store_name = SettingsModel.get_setting('store_name', 'Thangam Stores')
        store_address = SettingsModel.get_setting('store_address', '')
        store_phone = SettingsModel.get_setting('store_phone', '')
        footer_text = SettingsModel.get_setting('receipt_footer', 'Thank you for shopping!')
        
        # Get paper width setting
        WIDTH = int(SettingsModel.get_setting('chars_per_line', '48'))
        line_spacing = SettingsModel.get_setting('line_spacing', 'Normal')
        
        # Calculate column widths based on paper width
        if WIDTH >= 48:
            item_col, qty_col, amt_col = 24, 8, 14
        elif WIDTH >= 42:
            item_col, qty_col, amt_col = 20, 8, 12
        else:
            item_col, qty_col, amt_col = 14, 6, 10
        
        spacing = "" if line_spacing == "Compact" else "\n" if line_spacing == "Relaxed" else ""
        
        # Build receipt text
        lines = []
        lines.append("=" * WIDTH)
        lines.append(f"{store_name[:WIDTH]:^{WIDTH}}")
        if store_address:
            if len(store_address) > WIDTH:
                lines.append(store_address[:WIDTH])
            else:
                lines.append(f"{store_address:^{WIDTH}}")
        if store_phone:
            lines.append(f"{'Ph: ' + store_phone:^{WIDTH}}")
        lines.append("=" * WIDTH)
        if spacing:
            lines.append(spacing)
        lines.append(f"Bill No: {bill_data['bill_number']}")
        lines.append(f"Date: {bill_data['date_time']}")
        lines.append(f"Customer: {bill_data.get('customer_name', 'Walk-in')[:WIDTH-10]}")
        if bill_data.get('customer_phone'):
            lines.append(f"Phone: {bill_data['customer_phone']}")
        if spacing:
            lines.append(spacing)
        lines.append("-" * WIDTH)
        lines.append(f"{'ITEM':<{item_col}} {'QTY':^{qty_col}} {'AMT':>{amt_col}}")
        lines.append("-" * WIDTH)
        
        for item in items:
            name = item['product_name'][:item_col]
            qty = f"{item['quantity']}{item['unit']}"[:qty_col]
            amt = f"{item['total']:.2f}"[:amt_col]
            lines.append(f"{name:<{item_col}} {qty:^{qty_col}} {amt:>{amt_col}}")
        
        lines.append("-" * WIDTH)
        if spacing:
            lines.append(spacing)
        
        label_col = WIDTH - amt_col - 2
        lines.append(f"{'Subtotal':<{label_col}} Rs.{bill_data['subtotal']:>{amt_col-3}.2f}")
        if bill_data.get('tax_amount') and bill_data['tax_amount'] > 0:
            lines.append(f"{'Tax':<{label_col}} Rs.{bill_data['tax_amount']:>{amt_col-3}.2f}")
        if bill_data.get('discount_amount') and bill_data['discount_amount'] > 0:
            lines.append(f"{'Discount':<{label_col}} -{bill_data['discount_amount']:>{amt_col-2}.2f}")
        if spacing:
            lines.append(spacing)
        lines.append("=" * WIDTH)
        lines.append(f"{'TOTAL':<{label_col}} Rs.{bill_data['grand_total']:>{amt_col-3}.2f}")
        lines.append("=" * WIDTH)
        if spacing:
            lines.append(spacing)
        lines.append(f"{'Pay: ' + bill_data.get('payment_method', 'Cash'):^{WIDTH}}")
        if spacing:
            lines.append(spacing)
        lines.append(f"{footer_text[:WIDTH]:^{WIDTH}}")
        lines.append(f"{'*** THANK YOU ***':^{WIDTH}}")
        lines.append("")
        lines.append("")
        lines.append("")
        
        receipt_text = "\n".join(lines)
        
        # ESC/POS commands: Initialize printer + Full cut
        # \x1b@ = Initialize printer, \x1dV\x00 = Full cut
        cut_bytes = b"\n\n\n\x1b@\x1dV\x00"
        raw_bytes = receipt_text.encode('cp437', errors='replace') + cut_bytes
        
        try:
            printed = False
            
            # Method 1: Direct RAW printing via win32print (best for thermal printers)
            try:
                import win32print
                hprinter = win32print.OpenPrinter(printer_name)
                try:
                    win32print.StartDocPrinter(hprinter, 1, ("Receipt", None, "RAW"))
                    try:
                        win32print.StartPagePrinter(hprinter)
                        win32print.WritePrinter(hprinter, raw_bytes)
                        win32print.EndPagePrinter(hprinter)
                    finally:
                        win32print.EndDocPrinter(hprinter)
                finally:
                    win32print.ClosePrinter(hprinter)
                printed = True
            except ImportError:
                error_logger.error("win32print not available")
            except Exception as e:
                error_logger.error(f"RAW print failed: {e}")
            
            # Method 2: PowerShell RAW printing fallback
            if not printed:
                try:
                    temp_file = os.path.join(tempfile.gettempdir(), f"receipt_{bill_data['bill_number'].replace('/', '_')}.bin")
                    with open(temp_file, 'wb') as f:
                        f.write(raw_bytes)
                    
                    ps_script = f'''
$printerName = "{printer_name}"
$bytes = [System.IO.File]::ReadAllBytes("{temp_file}")
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class RawPrinter {{
    [DllImport("winspool.drv", CharSet = CharSet.Unicode, SetLastError = true)]
    public static extern bool OpenPrinter(string pPrinterName, out IntPtr phPrinter, IntPtr pDefault);
    [DllImport("winspool.drv", SetLastError = true)]
    public static extern bool ClosePrinter(IntPtr hPrinter);
    [DllImport("winspool.drv", CharSet = CharSet.Unicode, SetLastError = true)]
    public static extern bool StartDocPrinter(IntPtr hPrinter, int Level, ref DOCINFO pDocInfo);
    [DllImport("winspool.drv", SetLastError = true)]
    public static extern bool EndDocPrinter(IntPtr hPrinter);
    [DllImport("winspool.drv", SetLastError = true)]
    public static extern bool StartPagePrinter(IntPtr hPrinter);
    [DllImport("winspool.drv", SetLastError = true)]
    public static extern bool EndPagePrinter(IntPtr hPrinter);
    [DllImport("winspool.drv", SetLastError = true)]
    public static extern bool WritePrinter(IntPtr hPrinter, byte[] pBytes, int dwCount, out int dwWritten);
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    public struct DOCINFO {{
        public string pDocName;
        public string pOutputFile;
        public string pDataType;
    }}
    public static bool SendToPrinter(string printerName, byte[] data) {{
        IntPtr hPrinter;
        if (!OpenPrinter(printerName, out hPrinter, IntPtr.Zero)) return false;
        DOCINFO di = new DOCINFO();
        di.pDocName = "Receipt";
        di.pDataType = "RAW";
        if (!StartDocPrinter(hPrinter, 1, ref di)) {{ ClosePrinter(hPrinter); return false; }}
        if (!StartPagePrinter(hPrinter)) {{ EndDocPrinter(hPrinter); ClosePrinter(hPrinter); return false; }}
        int written;
        bool success = WritePrinter(hPrinter, data, data.Length, out written);
        EndPagePrinter(hPrinter);
        EndDocPrinter(hPrinter);
        ClosePrinter(hPrinter);
        return success;
    }}
}}
"@ -ErrorAction SilentlyContinue
[RawPrinter]::SendToPrinter($printerName, $bytes)
'''
                    result = subprocess.run(
                        ['powershell', '-ExecutionPolicy', 'Bypass', '-Command', ps_script],
                        capture_output=True, text=True, timeout=30
                    )
                    if result.returncode == 0:
                        printed = True
                    
                    # Cleanup temp file
                    try:
                        import threading
                        def cleanup():
                            import time
                            time.sleep(5)
                            try:
                                os.remove(temp_file)
                            except:
                                pass
                        threading.Thread(target=cleanup, daemon=True).start()
                    except:
                        pass
                except Exception as e:
                    error_logger.error(f"PowerShell RAW print failed: {e}")
            
            if printed:
                transaction_logger.info(f"Printed bill {bill_data['bill_number']} to {printer_name}")
            else:
                raise PrinterError("All print methods failed")
                
        except subprocess.TimeoutExpired:
            raise PrinterError("Print timed out")
        except Exception as e:
            error_logger.error(f"Windows print failed: {e}")
            raise PrinterError(f"Windows print failed: {e}")

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
