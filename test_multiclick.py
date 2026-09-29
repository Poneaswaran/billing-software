import os
import sys
import time

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QMouseEvent

app = QApplication.instance() or QApplication(sys.argv)
from app.ui_main import MainWindow

def test_clicks():
    print("Testing multi-click behavior on search bar...")
    win = MainWindow()
    win.show()

    assert len(win.products) > 0, "Should have products in local database"
    search = win.prod_search

    # Test 1: First click -> dropdown opens
    print("[Click 1] First click on search bar...")
    ev1 = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPointF(10, 10), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    search.mousePressEvent(ev1)
    app.processEvents()
    assert search.popup.isVisible(), "Popup should be open on 1st click"
    print("[OK] Popup is OPEN on 1st click")

    # Test 2: Second click while open -> dropdown toggles closed
    print("[Click 2] Second click while open (toggle close)...")
    ev2 = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPointF(10, 10), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    search.mousePressEvent(ev2)
    app.processEvents()
    assert not search.popup.isVisible(), "Popup should close on toggle click"
    print("[OK] Popup is CLOSED on 2nd toggle click")

    # Test 3: Third click while closed -> dropdown opens again!
    time.sleep(0.3)
    print("[Click 3] Third click after toggle -> dropdown reopens...")
    ev3 = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPointF(10, 10), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    search.mousePressEvent(ev3)
    app.processEvents()
    assert search.popup.isVisible(), "Popup should reopen on 3rd click"
    print("[OK] Popup is OPEN on 3rd click")

    # Test 4: Select an item from dropdown
    print("[Selection] User clicks a product in the dropdown...")
    item0 = search.popup.list_widget.item(0)
    search.popup._on_item_clicked(item0)
    app.processEvents()
    assert not search.popup.isVisible(), "Popup should close after item selection"
    assert len(win.cart) == 1, "Product should be added to cart"
    print(f"[OK] Product selected into cart. Cart count: {len(win.cart)}. Popup is closed.")

    # Test 5: Click on search bar AGAIN after item selection
    time.sleep(0.3)
    print("[Click 4] Click on search bar after previous item selection...")
    ev4 = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPointF(10, 10), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    search.mousePressEvent(ev4)
    app.processEvents()
    assert search.popup.isVisible(), "Popup should reopen when clicked after previous selection"
    print("[OK] Popup is OPEN on click after item selection")

    # Clean exit
    search.popup.hide()
    if win.conn_checker:
        win.conn_checker.wait(2000)
    if win.daily_sync_worker:
        win.daily_sync_worker.wait(2000)

    print("\n[SUCCESS] Multi-click toggle and reopening test PASSED 100%!")

if __name__ == '__main__':
    test_clicks()
