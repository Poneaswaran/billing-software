import os
import time
from PyQt6.QtWidgets import (
    QLineEdit, QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
    QListWidget, QListWidgetItem, QWidget, QGraphicsDropShadowEffect,
    QApplication, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QSize, QEvent, QTimer
from PyQt6.QtGui import QPixmap, QColor, QFont, QCursor, QPainter, QPen, QBrush

from app.image_loader import ImageLoader, create_placeholder_pixmap

class ProductDropdownItemWidget(QWidget):
    """Custom widget rendered for every product item inside the search dropdown."""
    def __init__(self, product: dict, toypop_connected: bool = False, is_dark: bool = False, parent=None):
        super().__init__(parent)
        self.product = product
        self.toypop_connected = toypop_connected
        self.is_dark = is_dark
        self.loader = ImageLoader.get_instance()
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(12)

        # Thumbnail Image Label
        self.lbl_img = QLabel()
        self.lbl_img.setFixedSize(48, 48)
        self.lbl_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if self.is_dark:
            self.lbl_img.setStyleSheet("background-color: #1a1e24; border: 1px solid #3d4450; border-radius: 6px;")
        else:
            self.lbl_img.setStyleSheet("background-color: #f4fbf6; border: 1px solid #d4edd9; border-radius: 6px;")

        self._load_thumbnail()
        layout.addWidget(self.lbl_img)

        # Text Details (Name, Code, Price, Stock)
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)

        top_line = QHBoxLayout()
        top_line.setContentsMargins(0, 0, 0, 0)
        
        name_str = self.product.get('name', 'Unknown')
        self.lbl_name = QLabel(name_str)
        if self.is_dark:
            self.lbl_name.setStyleSheet("font-weight: bold; font-size: 13px; color: #f5f6fa; background: transparent;")
        else:
            self.lbl_name.setStyleSheet("font-weight: bold; font-size: 13px; color: #1c3f2d; background: transparent;")
        top_line.addWidget(self.lbl_name)

        top_line.addStretch()

        price_val = float(self.product.get('price_per_unit', 0))
        self.lbl_price = QLabel(f"₹{price_val:.2f}")
        if self.is_dark:
            self.lbl_price.setStyleSheet("font-weight: bold; font-size: 14px; color: #4cd137; background: transparent;")
        else:
            self.lbl_price.setStyleSheet("font-weight: bold; font-size: 14px; color: #2e7d32; background: transparent;")
        top_line.addWidget(self.lbl_price)

        info_layout.addLayout(top_line)

        # Subtitle (Code / Barcode, Category, Stock)
        code = self.product.get('code', '')
        stock = self.product.get('stock_qty', 0)
        category = self.product.get('category', 'General')
        sub_text = f"SKU: {code}  •  Category: {category}  •  Stock: {stock}"
        self.lbl_sub = QLabel(sub_text)
        if self.is_dark:
            self.lbl_sub.setStyleSheet("font-size: 11px; color: #8892a0; background: transparent;")
        else:
            self.lbl_sub.setStyleSheet("font-size: 11px; color: #666666; background: transparent;")
        info_layout.addWidget(self.lbl_sub)

        layout.addLayout(info_layout, 1)

    def _load_thumbnail(self):
        img_url = self.product.get('image_url')
        if self.toypop_connected and img_url:
            cached = self.loader.load_image(img_url)
            if cached and not cached.isNull():
                self._set_pixmap(cached)
            else:
                self.lbl_img.setPixmap(create_placeholder_pixmap(48, 48, "", "Loading", is_dark=self.is_dark))
                self.loader.image_ready.connect(self._on_image_loaded)
        else:
            self.lbl_img.setPixmap(create_placeholder_pixmap(48, 48, "", "ToyPop", is_dark=self.is_dark))

    def _on_image_loaded(self, url: str, pixmap: QPixmap):
        if self.product.get('image_url') == url:
            self._set_pixmap(pixmap)

    def _set_pixmap(self, pixmap: QPixmap):
        scaled = pixmap.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        # Crop center square
        x = (scaled.width() - 48) // 2
        y = (scaled.height() - 48) // 2
        cropped = scaled.copy(x, y, 48, 48)
        self.lbl_img.setPixmap(cropped)


class ProductSearchDropdownPopup(QFrame):
    """Dropdown popup showing all local products with thumbnail images and search filtering."""
    product_selected = pyqtSignal(dict)

    def __init__(self, parent_input=None):
        parent_window = parent_input.window() if parent_input else None
        super().__init__(parent_window, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.parent_input = parent_input
        self.products = []
        self.filtered_products = []
        self.toypop_connected = False
        self.theme = 'Light'
        self.last_hide_time = 0
        self.init_ui()

    def hideEvent(self, event):
        self.last_hide_time = time.time()
        super().hideEvent(event)

    def init_ui(self):
        self.setObjectName("productDropdownPopup")

        # Add drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 90))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Header bar
        header_bar = QHBoxLayout()
        header_bar.setContentsMargins(6, 4, 6, 4)
        
        self.lbl_header = QLabel("📦 Products in Database")
        header_bar.addWidget(self.lbl_header)

        header_bar.addStretch()

        self.lbl_conn = QLabel("⚪ Offline")
        header_bar.addWidget(self.lbl_conn)

        layout.addLayout(header_bar)

        # List Widget
        self.list_widget = QListWidget()
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        self.list_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self.list_widget)

        # Apply saved or initial theme
        try:
            from app.models import SettingsModel
            saved_theme = SettingsModel.get_setting('theme', 'Light')
        except Exception:
            saved_theme = 'Light'
        self.apply_theme(saved_theme)

    def apply_theme(self, theme_name: str = 'Light'):
        self.theme = theme_name
        is_dark = (theme_name == 'Dark')
        if is_dark:
            self.setStyleSheet("""
                QFrame#productDropdownPopup {
                    background-color: #232830;
                    border: 2px solid #4caf50;
                    border-radius: 8px;
                }
                QListWidget {
                    border: none;
                    background-color: transparent;
                    outline: none;
                }
                QListWidget::item {
                    border-bottom: 1px solid #333945;
                    padding: 2px;
                    background-color: transparent;
                }
                QListWidget::item:selected {
                    background-color: #1d3d2c;
                    border-radius: 4px;
                }
                QListWidget::item:hover {
                    background-color: #2c323d;
                    border-radius: 4px;
                }
            """)
            self.lbl_header.setStyleSheet("font-weight: bold; font-size: 11px; color: #81c784; text-transform: uppercase;")
            if self.toypop_connected:
                self.lbl_conn.setStyleSheet("font-size: 10px; color: #4cd137; font-weight: bold;")
            else:
                self.lbl_conn.setStyleSheet("font-size: 10px; color: #8892a0; font-weight: bold;")
        else:
            self.setStyleSheet("""
                QFrame#productDropdownPopup {
                    background-color: #ffffff;
                    border: 2px solid #2e7d32;
                    border-radius: 8px;
                }
                QListWidget {
                    border: none;
                    background-color: transparent;
                    outline: none;
                }
                QListWidget::item {
                    border-bottom: 1px solid #f0f0f0;
                    padding: 2px;
                    background-color: transparent;
                }
                QListWidget::item:selected {
                    background-color: #e8f5e9;
                    border-radius: 4px;
                }
                QListWidget::item:hover {
                    background-color: #f4fbf6;
                    border-radius: 4px;
                }
            """)
            self.lbl_header.setStyleSheet("font-weight: bold; font-size: 11px; color: #2e7d32; text-transform: uppercase;")
            if self.toypop_connected:
                self.lbl_conn.setStyleSheet("font-size: 10px; color: #2e7d32; font-weight: bold;")
            else:
                self.lbl_conn.setStyleSheet("font-size: 10px; color: #777777; font-weight: bold;")

        # Refresh list widget items to reflect updated theme colors
        if self.products:
            self.filter_products(self.parent_input.text() if self.parent_input else "")

    def set_toypop_connected(self, connected: bool):
        self.toypop_connected = connected
        is_dark = (getattr(self, 'theme', 'Light') == 'Dark')
        if connected:
            self.lbl_conn.setText("🟢 ToyPop Cloud Connected")
            color = "#4cd137" if is_dark else "#2e7d32"
            self.lbl_conn.setStyleSheet(f"font-size: 10px; color: {color}; font-weight: bold;")
        else:
            self.lbl_conn.setText("⚪ ToyPop Offline")
            color = "#8892a0" if is_dark else "#777777"
            self.lbl_conn.setStyleSheet(f"font-size: 10px; color: {color}; font-weight: bold;")

    def set_products(self, products: list):
        self.products = products or []
        self.filter_products(self.parent_input.text() if self.parent_input else "")

    def filter_products(self, query: str = ""):
        """Filters products by query. If query is empty, displays ALL products in local DB."""
        q = (query or "").strip().lower()
        if not q:
            self.filtered_products = list(self.products)
        else:
            self.filtered_products = [
                p for p in self.products
                if q in p.get('name', '').lower()
                or q in p.get('code', '').lower()
                or q in p.get('category', '').lower()
                or any(q in str(alias).lower() for alias in p.get('aliases', []))
            ]

        self.lbl_header.setText(f"📦 Products in Database ({len(self.filtered_products)} of {len(self.products)})")
        self.list_widget.clear()

        is_dark = (getattr(self, 'theme', 'Light') == 'Dark')
        for p in self.filtered_products:
            item = QListWidgetItem(self.list_widget)
            item.setSizeHint(QSize(400, 62))
            widget = ProductDropdownItemWidget(p, self.toypop_connected, is_dark=is_dark)
            self.list_widget.setItemWidget(item, widget)

        if self.filtered_products:
            self.list_widget.setCurrentRow(0)

    def _on_item_clicked(self, item: QListWidgetItem):
        row = self.list_widget.row(item)
        if 0 <= row < len(self.filtered_products):
            prod = self.filtered_products[row]
            self.product_selected.emit(prod)
            self.hide()

    def get_selected_product(self):
        row = self.list_widget.currentRow()
        if 0 <= row < len(self.filtered_products):
            return self.filtered_products[row]
        return None

    def select_next(self):
        row = self.list_widget.currentRow()
        if row < self.list_widget.count() - 1:
            self.list_widget.setCurrentRow(row + 1)

    def select_prev(self):
        row = self.list_widget.currentRow()
        if row > 0:
            self.list_widget.setCurrentRow(row - 1)


class ProductSearchLineEdit(QLineEdit):
    """
    Search LineEdit that drops down ALL local database products on click
    and updates live product images when ToyPop Cloud is connected.
    """
    product_selected = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("prodSearch")
        self.setPlaceholderText("📦 Click to browse products or scan barcode...")
        self.setMinimumHeight(42)

        self.popup = ProductSearchDropdownPopup(self)
        self.popup.product_selected.connect(self._on_popup_product_selected)

        # Apply saved or default theme
        try:
            from app.models import SettingsModel
            saved_theme = SettingsModel.get_setting('theme', 'Light')
        except Exception:
            saved_theme = 'Light'
        self.apply_theme(saved_theme)

        self.textChanged.connect(self._on_text_changed)

    def apply_theme(self, theme_name: str = 'Light'):
        is_dark = (theme_name == 'Dark')
        if is_dark:
            self.setStyleSheet("""
                QLineEdit#prodSearch {
                    padding: 6px 12px;
                    font-size: 13px;
                    border: 2px solid #3d84b8;
                    border-radius: 6px;
                    background-color: #2c323d;
                    color: #ffffff;
                    selection-background-color: #00a8ff;
                    placeholder-text-color: #8892a0;
                }
                QLineEdit#prodSearch:focus {
                    border: 2px solid #4caf50;
                    background-color: #353c48;
                }
            """)
        else:
            self.setStyleSheet("""
                QLineEdit#prodSearch {
                    padding: 6px 12px;
                    font-size: 13px;
                    border: 2px solid #2196F3;
                    border-radius: 6px;
                    background-color: #ffffff;
                    color: #2f3640;
                    selection-background-color: #00a8ff;
                    placeholder-text-color: #888888;
                }
                QLineEdit#prodSearch:focus {
                    border: 2px solid #2e7d32;
                    background-color: #fcfffd;
                }
            """)
        if hasattr(self, 'popup'):
            self.popup.apply_theme(theme_name)


    def set_toypop_connected(self, connected: bool):
        self.popup.set_toypop_connected(connected)

    def set_products(self, products: list):
        self.popup.set_products(products)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        now = time.time()
        # If the dropdown was closed within 250ms by clicking the search bar,
        # treat this click as a toggle close and do not reopen.
        if (now - getattr(self.popup, 'last_hide_time', 0)) < 0.25:
            return
        if self.popup.isVisible():
            self.popup.hide()
        else:
            QTimer.singleShot(0, self.show_dropdown)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        # Open dropdown when tabbed into by keyboard, but not on programmatic setFocus
        if event.reason() in (Qt.FocusReason.TabFocusReason, Qt.FocusReason.BacktabFocusReason):
            QTimer.singleShot(0, self.show_dropdown)

    def show_dropdown(self):
        """Displays dropdown popup populated with all products in local database."""
        self.popup.filter_products(self.text())
        if not self.popup.filtered_products:
            self.popup.filter_products("")
        
        # Position popup directly beneath the search input
        global_pos = self.mapToGlobal(QPoint(0, self.height() + 2))
        width = max(self.width(), 560)
        item_count = len(self.popup.filtered_products)
        height = min(420, max(120, item_count * 64 + 40))
        
        self.popup.setGeometry(global_pos.x(), global_pos.y(), width, height)
        self.popup.show()
        self.popup.raise_()

    def _on_text_changed(self, text: str):
        if self.hasFocus():
            self.popup.filter_products(text)
            if not self.popup.isVisible():
                QTimer.singleShot(0, self.show_dropdown)
            else:
                height = min(420, max(100, len(self.popup.filtered_products) * 64 + 40))
                self.popup.resize(self.popup.width(), height)

    def keyPressEvent(self, event):
        if self.popup.isVisible():
            if event.key() == Qt.Key.Key_Down:
                self.popup.select_next()
                return
            elif event.key() == Qt.Key.Key_Up:
                self.popup.select_prev()
                return
            elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                prod = self.popup.get_selected_product()
                if prod:
                    self._on_popup_product_selected(prod)
                    return
            elif event.key() == Qt.Key.Key_Escape:
                self.popup.hide()
                return

        super().keyPressEvent(event)

    def _on_popup_product_selected(self, product: dict):
        self.popup.hide()
        self.clear()
        self.product_selected.emit(product)
