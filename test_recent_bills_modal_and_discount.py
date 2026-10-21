import sys
import os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Set offscreen for automated testing without window system
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer

# Ensure app is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db import init_db
from app.sync import ensure_db_columns
from app.models import ProductModel, CustomerModel, BillModel
from app.ui_main import MainWindow, RecentBillActionDialog

def test_recent_bills_and_discount():
    print("[1] Initializing DB and creating QApplication...")
    init_db()
    ensure_db_columns()
    app = QApplication.instance() or QApplication(sys.argv)

    print("[2] Creating MainWindow...")
    win = MainWindow()

    print("[3] Testing Discount Feature (Number and Percentage)...")
    # Add dummy item to cart: price 500, qty 2 => subtotal 1000
    win.cart = [{
        'product_id': 1,
        'product_name': 'Test Toy Robot',
        'quantity': 2,
        'unit': 'pcs',
        'price': 500.0,
        'total': 1000.0
    }]
    win.update_cart_table()
    assert win.lbl_subtotal.text() == "₹1000.00", f"Expected ₹1000.00 subtotal, got {win.lbl_subtotal.text()}"

    # Test 10% discount
    win.discount_type.setCurrentText("%")
    win.discount_input.setText("10")
    win.update_cart_table()
    assert win.lbl_discount_amt.text() == "₹100.00", f"Expected ₹100.00 discount amt, got {win.lbl_discount_amt.text()}"
    assert win.lbl_grand_total.text() == "₹900.00", f"Expected ₹900.00 grand total, got {win.lbl_grand_total.text()}"
    print("    [OK] Percentage discount (10% of Rs.1000 = Rs.100.00, Total Rs.900.00) verified!")

    # Test Fixed Rupee (Number) discount: ₹150
    win.discount_type.setCurrentText("₹")
    win.discount_input.setText("150")
    win.update_cart_table()
    assert win.lbl_discount_amt.text() == "₹150.00", f"Expected ₹150.00 discount amt, got {win.lbl_discount_amt.text()}"
    assert win.lbl_grand_total.text() == "₹850.00", f"Expected ₹850.00 grand total, got {win.lbl_grand_total.text()}"
    print("    [OK] Fixed Number discount (Rs.150.00 on Rs.1000 = Total Rs.850.00) verified!")

    # Test smart text auto-switching (e.g. typing "20%" switches mode to '%')
    win.discount_input.setText("20%")
    win.update_cart_table()
    assert win.discount_type.currentText() == "%", "Expected discount_type to auto-switch to '%'"
    assert win.lbl_discount_amt.text() == "₹200.00", f"Expected ₹200.00 discount amt, got {win.lbl_discount_amt.text()}"
    assert win.lbl_grand_total.text() == "₹800.00", f"Expected ₹800.00 grand total, got {win.lbl_grand_total.text()}"
    print("    [OK] Auto-switch to '%' on typing '20%' verified!")

    # Test smart text auto-switching with ₹
    win.discount_input.setText("₹75")
    win.update_cart_table()
    assert win.discount_type.currentText() == "₹", "Expected discount_type to auto-switch to '₹'"
    assert win.lbl_discount_amt.text() == "₹75.00", f"Expected ₹75.00 discount amt, got {win.lbl_discount_amt.text()}"
    assert win.lbl_grand_total.text() == "₹925.00", f"Expected ₹925.00 grand total, got {win.lbl_grand_total.text()}"
    print("    [OK] Auto-switch to '₹' on typing '₹75' verified!")

    print("[4] Creating a test bill in DB to test Recent Bills modal...")
    from app.utils.helpers import generate_bill_number
    from datetime import datetime
    test_bill_num = generate_bill_number()
    bill_data = {
        'bill_number': test_bill_num,
        'customer_id': None,
        'subtotal': 1000.0,
        'grand_total': 925.0,
        'discount_amount': 75.0,
        'payment_method': 'Cash',
        'customer_name': 'Walk-in Customer',
        'customer_phone': '',
        'date_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    bill_id = BillModel.create_bill(bill_data, win.cart)
    assert bill_id is not None, "Failed to create bill in DB"
    bill_data['id'] = bill_id

    print("[5] Testing Recent Bills list loading & click handler...")
    win.load_recent_bills()
    assert win.recent_list.count() > 0, "Recent list should have at least 1 bill"
    first_item = win.recent_list.item(0)
    assert first_item is not None
    loaded_data = first_item.data(Qt.ItemDataRole.UserRole)
    assert loaded_data is not None, "Recent list item must have bill_data stored"
    print(f"    [OK] Loaded recent bill: {loaded_data['bill_number']} - Rs.{loaded_data['grand_total']:.2f}")

    print("[6] Testing RecentBillActionDialog (Preview Bill, Add More Items, Close)...")
    items = BillModel.get_bill_items(bill_id)
    assert len(items) == 1, f"Expected 1 item, got {len(items)}"
    assert items[0]['product_name'] == 'Test Toy Robot'

    modal = RecentBillActionDialog(win, loaded_data, items)
    # Check that modal has the required buttons
    buttons = modal.findChildren(modal.findChild(type(modal)).__class__) # or inspect layouts
    assert hasattr(modal, 'preview_bill'), "Modal must have preview_bill method"
    assert hasattr(modal, 'add_more_items'), "Modal must have add_more_items method"

    # Test "Add More Items" action
    modal.add_more_items()
    assert modal.action_selected == 'add_items', "Expected action_selected to be 'add_items'"
    print("    [OK] RecentBillActionDialog created and 'add_items' action verified!")

    print("[7] Testing load_bill_for_adding_items into MainWindow...")
    win.clear_cart()
    assert len(win.cart) == 0, "Cart should be empty after clear_cart"
    assert win.editing_bill_id is None

    win.load_bill_for_adding_items(loaded_data, items)
    assert win.editing_bill_id == loaded_data['id'], f"Expected editing_bill_id {loaded_data['id']}, got {win.editing_bill_id}"
    assert win.editing_bill_number == loaded_data['bill_number']
    assert len(win.cart) == 1, f"Expected 1 item loaded into cart, got {len(win.cart)}"
    assert not win.banner_editing.isHidden(), "Editing banner must be shown (not hidden)"
    assert win.discount_input.text() == "75", f"Expected discount 75 restored, got {win.discount_input.text()}"
    print("    [OK] Bill successfully loaded for adding items (Cart, Customer, Discount, Banner active)!")

    # Add a second item to the bill
    win.cart.append({
        'product_id': 2,
        'product_name': 'Wooden Puzzle',
        'quantity': 1,
        'unit': 'pcs',
        'price': 300.0,
        'total': 300.0
    })
    win.update_cart_table()
    assert win.lbl_subtotal.text() == "₹1300.00"

    print("[8] Testing BillModel.update_bill with updated items and subtotal...")
    updated_bill_data = dict(loaded_data)
    updated_bill_data['subtotal'] = 1300.0
    updated_bill_data['grand_total'] = 1225.0
    updated_bill_data['discount_amount'] = 75.0
    BillModel.update_bill(win.editing_bill_id, updated_bill_data, win.cart)

    updated_items = BillModel.get_bill_items(bill_id)
    assert len(updated_items) == 2, f"Expected 2 items after update, got {len(updated_items)}"
    updated_bill = BillModel.get_bill_by_id(bill_id)
    assert updated_bill['grand_total'] == 1225.0, f"Expected ₹1225.0, got {updated_bill['grand_total']}"
    assert updated_bill['synced'] == 0, "Updated bill must have synced=0 for cloud re-sync"
    print("    [OK] Bill successfully updated in SQLite preserving bill_number and marking synced=0!")

    print("[9] Testing cancel_bill_edit and clear_cart...")
    win.clear_cart()
    assert win.editing_bill_id is None
    assert win.editing_bill_number is None
    assert win.banner_editing.isHidden() is True
    assert len(win.cart) == 0
    print("    [OK] Clear cart resets editing state and hides banner successfully!")

    if win.conn_checker:
        win.conn_checker.wait(2000)
    if win.daily_sync_worker:
        win.daily_sync_worker.wait(3000)

    print("\n[SUCCESS] All recent bill modal, preview, add items, and number/percentage discount tests passed!")
    os._exit(0)

if __name__ == '__main__':
    test_recent_bills_and_discount()
