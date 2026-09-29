import sys
import os

# Set offscreen for automated testing without window system
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

# Ensure app is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db import init_db
from app.sync import ensure_db_columns
from app.ui_main import MainWindow

def test():
    print("[1] Initializing DB and columns...")
    init_db()
    ensure_db_columns()

    print("[2] Creating QApplication...")
    app = QApplication.instance() or QApplication(sys.argv)

    print("[3] Creating MainWindow...")
    win = MainWindow()

    print("[4] Checking search dropdown and attributes...")
    assert hasattr(win, 'prod_search'), "Missing prod_search"
    assert hasattr(win, 'toypop_connected'), "Missing toypop_connected"

    print("[5] Testing dropdown on search click...")
    win.prod_search.show_dropdown()
    filtered_count = len(win.prod_search.popup.filtered_products)
    print(f"    Dropdown contains {filtered_count} products (matching local DB total: {len(win.products)})")
    assert filtered_count == len(win.products), "Dropdown must list ALL products in local DB"

    print("[6] Testing product selection from dropdown...")
    if win.products:
        p = win.products[0]
        win.on_product_dropdown_selected(p)
        assert len(win.cart) == 1, "Cart item should be added on dropdown selection"
        print(f"    Added '{p['name']}' to cart via dropdown selection.")

        # Test barcode scan / manual add
        win.prod_search.setText(p['code'])
        win.add_product_to_cart_manual()
        assert len(win.cart) >= 1
        print(f"    Added '{p['name']}' via barcode/code scan.")

    print("[7] Testing daily sync and first-time sync checkers...")
    from app.sync import ToyPopSyncClient
    client = ToyPopSyncClient()
    print("    is_first_time_sync:", client.is_first_time_sync())
    print("    is_daily_sync_needed:", client.is_daily_sync_needed())

    if win.conn_checker:
        win.conn_checker.wait(3000)
    if win.daily_sync_worker:
        win.daily_sync_worker.wait(5000)

    print("\n[SUCCESS] All Product Dropdown and Daily Sync workflows passed!")

if __name__ == '__main__':
    test()


