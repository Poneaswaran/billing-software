from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QDialog,
    QGraphicsDropShadowEffect, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QColor, QCursor, QFont
from app.image_loader import ImageLoader, create_placeholder_pixmap

class ClickableImageLabel(QLabel):
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class ProductImageDialog(QDialog):
    """Enlarged modal display of the product's image with key attributes."""
    def __init__(self, parent=None, product=None, pixmap=None):
        super().__init__(parent)
        self.product = product or {}
        self.pixmap = pixmap
        self.setWindowTitle(f"ToyPop Product - {self.product.get('name', 'Product Image')}")
        self.resize(520, 580)
        self.setModal(True)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header info
        title = QLabel(self.product.get('name', 'Unknown Product'))
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1b5e20;")
        title.setWordWrap(True)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        code_lbl = QLabel(f"SKU / Barcode: {self.product.get('code', 'N/A')}  |  Category: {self.product.get('category', 'General')}")
        code_lbl.setStyleSheet("color: #666; font-size: 12px;")
        code_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(code_lbl)

        # Image Display Area
        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_label.setStyleSheet("background-color: #f8faf9; border: 1px solid #d4edd9; border-radius: 12px;")
        self.img_label.setMinimumSize(460, 400)

        if self.pixmap and not self.pixmap.isNull():
            scaled = self.pixmap.scaled(460, 400, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.img_label.setPixmap(scaled)
        else:
            self.img_label.setPixmap(create_placeholder_pixmap(460, 400, "ToyPop Cloud", "No Full Image Available"))

        layout.addWidget(self.img_label, 1)

        # Price & Action
        bottom_layout = QHBoxLayout()
        price_paise = self.product.get('price_per_unit', 0)
        price_lbl = QLabel(f"Price: ₹{price_paise:.2f}")
        price_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #2e7d32;")
        bottom_layout.addWidget(price_lbl)

        bottom_layout.addStretch()

        btn_close = QPushButton("Close")
        btn_close.setFixedWidth(100)
        btn_close.clicked.connect(self.accept)
        bottom_layout.addWidget(btn_close)

        layout.addLayout(bottom_layout)


class ProductPreviewCard(QFrame):
    """
    Card widget embedded in POS layout that shows the first image and details
    of a product when scanned or clicked via 'Scan Barcode or Search Product'.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_product = None
        self.current_pixmap = None
        self.current_image_url = None
        self.toypop_connected = False
        
        self.loader = ImageLoader.get_instance()
        self.loader.image_ready.connect(self._on_image_ready)
        self.loader.image_error.connect(self._on_image_error)

        self.init_ui()

    def init_ui(self):
        self.setObjectName("productPreviewCard")
        self.setStyleSheet("""
            QFrame#productPreviewCard {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 10px;
                padding: 10px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Top Header Bar
        top_bar = QHBoxLayout()
        self.lbl_title = QLabel("📦 Scanned Product")
        self.lbl_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #1c3f2d;")
        
        self.lbl_conn_badge = QLabel("⚪ Offline")
        self.lbl_conn_badge.setStyleSheet("""
            background-color: #eeeeee;
            color: #777777;
            font-size: 11px;
            font-weight: bold;
            padding: 3px 8px;
            border-radius: 10px;
        """)
        
        top_bar.addWidget(self.lbl_title)
        top_bar.addStretch()
        top_bar.addWidget(self.lbl_conn_badge)
        layout.addLayout(top_bar)

        # Image Container
        img_container = QFrame()
        img_container.setStyleSheet("background-color: #f7faf8; border: 1px solid #e2f0e6; border-radius: 8px;")
        img_layout = QVBoxLayout(img_container)
        img_layout.setContentsMargins(4, 4, 4, 4)
        img_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.image_label = ClickableImageLabel()
        self.image_label.setFixedSize(190, 160)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setToolTip("Click to enlarge image")
        self.image_label.clicked.connect(self._open_image_modal)
        
        img_layout.addWidget(self.image_label)
        layout.addWidget(img_container)

        # Product Title
        self.lbl_name = QLabel("No Product Selected")
        self.lbl_name.setStyleSheet("font-weight: bold; font-size: 13px; color: #222;")
        self.lbl_name.setWordWrap(True)
        self.lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_name)

        # Price & Code
        self.lbl_price = QLabel("₹0.00")
        self.lbl_price.setStyleSheet("font-size: 15px; font-weight: bold; color: #1b5e20;")
        self.lbl_price.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_price)

        self.lbl_meta = QLabel("Scan a barcode or search a product")
        self.lbl_meta.setStyleSheet("font-size: 11px; color: #666;")
        self.lbl_meta.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_meta)

        self.update_connection_status(False)
        self.clear_preview()

    def set_connection_status(self, connected: bool):
        """Updates the card's connection state and badge."""
        self.toypop_connected = connected
        if connected:
            self.lbl_conn_badge.setText("🟢 ToyPop Online")
            self.lbl_conn_badge.setStyleSheet("""
                background-color: #e8f5e9;
                color: #2e7d32;
                font-size: 11px;
                font-weight: bold;
                padding: 3px 8px;
                border-radius: 10px;
                border: 1px solid #c8e6c9;
            """)
        else:
            self.lbl_conn_badge.setText("⚪ ToyPop Offline")
            self.lbl_conn_badge.setStyleSheet("""
                background-color: #f5f5f5;
                color: #888888;
                font-size: 11px;
                font-weight: bold;
                padding: 3px 8px;
                border-radius: 10px;
            """)
        # If product is currently displayed, refresh view state
        if self.current_product:
            self.show_product(self.current_product)

    def update_connection_status(self, connected: bool):
        self.set_connection_status(connected)

    def clear_preview(self):
        """Resets preview to empty state."""
        self.current_product = None
        self.current_pixmap = None
        self.current_image_url = None
        self.lbl_name.setText("Ready to Scan / Search")
        self.lbl_price.setText("₹0.00")
        self.lbl_meta.setText("Scan barcode or search product to view image")
        placeholder = create_placeholder_pixmap(190, 160, "ToyPop POS", "Ready to Scan")
        self.image_label.setPixmap(placeholder)

    def show_product(self, product: dict):
        """Displays product metadata and its first image when ToyPop is connected."""
        if not product:
            self.clear_preview()
            return

        self.current_product = product
        name = product.get('name', 'Unknown')
        code = product.get('code', '')
        price = product.get('price_per_unit', 0.0)
        stock = product.get('stock_qty', 0)
        image_url = product.get('image_url')

        self.lbl_name.setText(name)
        self.lbl_price.setText(f"₹{price:.2f}")
        self.lbl_meta.setText(f"Code: {code}  |  Stock: {stock}")

        # When ToyPop is connected, display the first image
        if self.toypop_connected:
            if image_url:
                self.current_image_url = image_url
                # Try loading image asynchronously
                cached = self.loader.load_image(image_url)
                if cached and not cached.isNull():
                    self._set_display_pixmap(cached)
                else:
                    loading_pixmap = create_placeholder_pixmap(190, 160, name[:16], "Loading Image...")
                    self.image_label.setPixmap(loading_pixmap)
            else:
                self.current_pixmap = None
                self.image_label.setPixmap(create_placeholder_pixmap(190, 160, name[:16], "No Image in Cloud"))
        else:
            # ToyPop not connected: inform user
            self.current_pixmap = None
            self.image_label.setPixmap(create_placeholder_pixmap(190, 160, "ToyPop Offline", "Connect to View Image"))

    def _set_display_pixmap(self, pixmap: QPixmap):
        self.current_pixmap = pixmap
        scaled = pixmap.scaled(190, 160, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.image_label.setPixmap(scaled)

    def _on_image_ready(self, url: str, pixmap: QPixmap):
        if self.current_image_url == url and self.toypop_connected:
            self._set_display_pixmap(pixmap)

    def _on_image_error(self, url: str, error: str):
        if self.current_image_url == url:
            self.current_pixmap = None
            prod_name = (self.current_product.get('name') if self.current_product else "ToyPop")[:16]
            self.image_label.setPixmap(create_placeholder_pixmap(190, 160, prod_name, "Image Load Failed"))

    def _open_image_modal(self):
        if self.current_product and self.toypop_connected:
            dlg = ProductImageDialog(self, self.current_product, self.current_pixmap)
            dlg.exec()
