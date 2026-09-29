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
from reportlab.graphics.barcode import code128
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF
try:
    import win32api
    import win32print
except ImportError:
    pass

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


def get_escpos_logo_bytes(logo_path, chars_per_line=48):
    """
    Convert image to ESC/POS raster bit image bytes (GS v 0).
    Centers the image by embedding it inside a white canvas matching paper printable dot width.
    - 80mm paper (chars_per_line >= 42): 576 dots printable width (72mm @ 203 DPI)
    - 58mm paper (chars_per_line < 42): 384 dots printable width (48mm @ 203 DPI)
    """
    if not logo_path or not os.path.exists(logo_path):
        return b""
    try:
        from PIL import Image
        from escpos.printer import Dummy

        img = Image.open(logo_path)
        # Handle alpha channel (transparency) by pasting onto a clean white background
        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
            img = img.convert('RGBA')
            bg = Image.new('RGB', img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[3])
            img = bg
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # Target printable width in dots
        paper_dots = 576 if chars_per_line >= 42 else 384
        max_logo_w = int(paper_dots * 0.85)

        w, h = img.size
        if w > max_logo_w:
            ratio = max_logo_w / float(w)
            new_h = max(1, int(h * ratio))
            img = img.resize((max_logo_w, new_h), Image.Resampling.LANCZOS)

        # Center on a full-width white canvas
        canvas = Image.new('RGB', (paper_dots, img.height), (255, 255, 255))
        offset_x = max(0, (paper_dots - img.width) // 2)
        canvas.paste(img, (offset_x, 0))

        d = Dummy()
        d.image(canvas, impl='bitImageRaster')
        return bytes(d.output)
    except Exception as e:
        error_logger.error(f"Failed to generate ESC/POS logo bytes: {e}")
        return b""


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

            logo_path = SettingsModel.get_setting('shop_logo_path', '')
            if logo_path and os.path.exists(logo_path):
                try:
                    from PIL import Image
                    img = Image.open(logo_path)
                    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                        img = img.convert('RGBA')
                        bg = Image.new('RGB', img.size, (255, 255, 255))
                        bg.paste(img, mask=img.split()[3])
                        img = bg
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                    paper_dots = 576
                    max_logo_w = int(paper_dots * 0.85)
                    if img.width > max_logo_w:
                        ratio = max_logo_w / float(img.width)
                        new_h = max(1, int(img.height * ratio))
                        img = img.resize((max_logo_w, new_h), Image.Resampling.LANCZOS)
                    canvas = Image.new('RGB', (paper_dots, img.height), (255, 255, 255))
                    canvas.paste(img, (max(0, (paper_dots - img.width) // 2), 0))
                    self.printer.image(canvas, impl='bitImageRaster')
                except Exception as e:
                    error_logger.error(f"Failed to print direct logo: {e}")

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
        logo_path = SettingsModel.get_setting('shop_logo_path', '')
        logo_bytes = get_escpos_logo_bytes(logo_path, WIDTH)

        init_bytes = b"\x1b@"
        cut_bytes = b"\n\n\n\x1b@\x1dV\x00"

        if logo_bytes:
            raw_bytes = init_bytes + logo_bytes + b"\n" + receipt_text.encode('cp437', errors='replace') + cut_bytes
        else:
            raw_bytes = init_bytes + receipt_text.encode('cp437', errors='replace') + cut_bytes
        
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
            header_message = SettingsModel.get_setting('header_message', '')
            logo_path = SettingsModel.get_setting('shop_logo_path', '')
            
            # Logo
            if logo_path and os.path.exists(logo_path):
                try:
                    # Draw logo at top center, 20mm high
                    c.drawImage(logo_path, width/2 - 25*mm, y, width=50*mm, height=20*mm, preserveAspectRatio=True)
                    y -= 25*mm # Move down
                except Exception:
                    pass

            c.setFont("Helvetica-Bold", 16)
            c.drawCentredString(width/2, y, store_name)
            y -= 8*mm
            
            if header_message:
                c.setFont("Helvetica-Oblique", 10)
                c.drawCentredString(width/2, y, header_message)
                y -= 8*mm
            
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
            error_logger.error(f"Email failed: {e}")
            raise PrinterError(f"Failed to send email: {e}")

    def print_barcode_label(self, product_data, count=1):
        """Generates and prints barcode labels for a product."""
        printer_name = SettingsModel.get_setting('windows_printer_name', '')
        if not printer_name:
            # Fallback to default if not set? OR just error. 
            # For now, let's try to get default if empty, or error.
            # actually win32print.GetDefaultPrinter() could work.
            try:
                printer_name = win32print.GetDefaultPrinter()
            except:
                raise PrinterError("No printer configured and no default printer found.")

        try:
            # Label size: 50mm x 25mm (Standard small label)
            # You might want to make this configurable in the future
            label_width = 50 * mm
            label_height = 25 * mm
            
            # Temporary file for the label
            temp_file = os.path.join(tempfile.gettempdir(), f"label_{product_data.get('code', 'ukn')}.pdf")
            
            c = canvas.Canvas(temp_file, pagesize=(label_width, label_height))
            
            store_name = SettingsModel.get_setting('store_name', 'Thangam Stores')
            price = product_data.get('price_per_unit', 0.0)
            name = product_data.get('name', 'Product')
            code = product_data.get('code', '')
            if not code:
                code = f"P{product_data.get('id')}" # Fallback internal code
            
            # Draw content
            # Store Name (Top, small)
            c.setFont("Helvetica-Bold", 6)
            c.drawCentredString(label_width / 2, label_height - 3*mm, store_name[:20])
            
            # Product Name (Below Store Name)
            c.setFont("Helvetica", 8)
            c.drawCentredString(label_width / 2, label_height - 6*mm, name[:20])
            
            # Barcode
            # reportlab barcode flow
            barcode = code128.Code128(code, barHeight=6*mm, barWidth=0.8) # Adjust barWidth to fit
            # We need to draw it on the canvas. 
            # Code128 width depends on data length.
            # Center it effectively
            # barcode.drawOn(c, x, y)
             
            # Calculate x to center (approx) - Code128 doesn't easily give width before drawing without render
            # But we can just try drawing it at a safe margin
            barcode_drawing = Drawing(label_width, 10*mm)
            barcode_drawing.add(barcode)
            # The barcode object itself handles x,y in its own coordinate system if we add it to Drawing?
            # actually barcode.drawOn(c, x, y) is easier.
            
            # Let's estimate width or just place it at 2mm margin
            barcode.drawOn(c, 2*mm, 8*mm)
            
            # Code Text (Human Readable)
            c.setFont("Helvetica", 7)
            c.drawCentredString(label_width / 2, 5*mm, code)
            
            # Price (Bottom Right or Centered)
            c.setFont("Helvetica-Bold", 9)
            c.drawCentredString(label_width / 2, 1.5*mm, f"Rs.{price:.2f}")
            
            c.showPage()
            c.save()
            
            # Print 'count' copies
            # Windows 'printto' verb prints to a specific printer
            # But it usually prints ONE copy. To print multiple, we loop.
            # NOTE: ShellExecute is async-ish and might open Adobe Reader.
            # A better way for silent printing of PDF to specific printer is tricky in pure Python without calling external tools like Acrobat with flags or Ghostscript.
            # However, for this task, 'os.startfile' or 'win32api.ShellExecute' is the standard "use system capabilities" way.
            
            for _ in range(count):
                win32api.ShellExecute(0, "printto", temp_file, f'"{printer_name}"', ".", 0)
                # Small delay to ensure order?
                import time
                time.sleep(1) 
                
            transaction_logger.info(f"Printed {count} labels for {name}")
            return True

        except Exception as e:
            error_logger.error(f"Label printing failed: {e}")
            raise PrinterError(f"Label printing failed: {e}")

    @staticmethod
    def list_usb_printers():
        """Lists connected USB printers (requires implementation specific to OS/Driver, using simple placeholders for now)."""
        # In a real scenario, we might iterate over /dev/usb/lp* or use win32print
        # python-escpos doesn't have a simple 'list all' static method that works universally without probing.
        # We will return a dummy list for UI demonstration if actual detection is hard.
        return [{"name": "Generic USB Printer", "vid": "0x0000", "pid": "0x0000"}]
