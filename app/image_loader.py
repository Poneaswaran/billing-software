import os
import hashlib
import urllib.request
import urllib.parse
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool, Qt
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QFont, QPen, QBrush

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "image_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

class ImageDownloadSignals(QObject):
    finished = pyqtSignal(str, QPixmap)
    failed = pyqtSignal(str, str)


class ImageDownloadWorker(QRunnable):
    """Background worker to download and cache product images without blocking UI."""
    def __init__(self, url: str, cache_path: str):
        super().__init__()
        self.url = url
        self.cache_path = cache_path
        self.signals = ImageDownloadSignals()

    def run(self):
        try:
            req = urllib.request.Request(
                self.url,
                headers={"User-Agent": "ToyPop-Billing-POS/1.0 (Windows)"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
                
            # Write to disk cache
            with open(self.cache_path, "wb") as f:
                f.write(data)

            pixmap = QPixmap()
            if pixmap.loadFromData(data):
                self.signals.finished.emit(self.url, pixmap)
            else:
                self.signals.failed.emit(self.url, "Invalid image format")
        except Exception as e:
            self.signals.failed.emit(self.url, str(e))


class ImageLoader(QObject):
    """Singleton-style asynchronous image loader and cacher for product images."""
    image_ready = pyqtSignal(str, QPixmap)
    image_error = pyqtSignal(str, str)

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ImageLoader()
        return cls._instance

    def __init__(self):
        super().__init__()
        self.memory_cache = {}
        self.pending_urls = set()

    def _get_cache_path(self, url: str) -> str:
        url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()
        # Extract extension if present
        ext = ".jpg"
        parsed = urllib.parse.urlparse(url)
        path = parsed.path.lower()
        for candidate in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
            if path.endswith(candidate):
                ext = candidate
                break
        return os.path.join(CACHE_DIR, f"{url_hash}{ext}")

    def load_image(self, url: str):
        """Loads an image asynchronously. Emits image_ready(url, pixmap) when available."""
        if not url:
            return None

        # Check memory cache first
        if url in self.memory_cache:
            pixmap = self.memory_cache[url]
            # Emit asynchronously on next loop so caller can connect signals if needed
            self.image_ready.emit(url, pixmap)
            return pixmap

        # Check disk cache
        cache_path = self._get_cache_path(url)
        if os.path.exists(cache_path):
            pixmap = QPixmap(cache_path)
            if not pixmap.isNull():
                self.memory_cache[url] = pixmap
                self.image_ready.emit(url, pixmap)
                return pixmap

        # If already downloading, wait for worker
        if url in self.pending_urls:
            return None

        self.pending_urls.add(url)
        worker = ImageDownloadWorker(url, cache_path)
        worker.signals.finished.connect(self._on_worker_finished)
        worker.signals.failed.connect(self._on_worker_failed)
        QThreadPool.globalInstance().start(worker)
        return None

    def _on_worker_finished(self, url: str, pixmap: QPixmap):
        self.pending_urls.discard(url)
        self.memory_cache[url] = pixmap
        self.image_ready.emit(url, pixmap)

    def _on_worker_failed(self, url: str, error: str):
        self.pending_urls.discard(url)
        self.image_error.emit(url, error)


def create_placeholder_pixmap(width: int = 180, height: int = 180, title: str = "ToyPop", subtitle: str = "No Image", is_dark: bool = False) -> QPixmap:
    """Generates a stylish vector-drawn placeholder pixmap when image is unavailable."""
    pixmap = QPixmap(width, height)
    
    if is_dark:
        bg_col = QColor("#1a1e24")
        border_col = QColor("#3d4450")
        box_bg = QColor("#252b34")
        box_border = QColor("#4caf50")
        icon_col = QColor("#81c784")
        title_col = QColor("#f5f6fa")
        sub_col = QColor("#8892a0")
    else:
        bg_col = QColor("#f4fbf6")
        border_col = QColor("#d4edd9")
        box_bg = QColor("#e8f5e9")
        box_border = QColor("#1b5e20")
        icon_col = QColor("#2e7d32")
        title_col = QColor("#1b5e20")
        sub_col = QColor("#66bb6a")

    pixmap.fill(bg_col)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Outer border
    border_pen = QPen(border_col, 2)
    painter.setPen(border_pen)
    painter.setBrush(QBrush(bg_col))
    painter.drawRoundedRect(1, 1, width - 2, height - 2, 8, 8)

    # Decorative inner icon box
    box_w = min(64, width - 10)
    box_h = min(56, height - 10)
    box_x = (width - box_w) // 2
    box_y = max(2, (height - box_h) // 2 - (10 if height > 80 else 0))
    painter.setPen(QPen(box_border, 1 if width < 60 else 2))
    painter.setBrush(QBrush(box_bg))
    painter.drawRoundedRect(box_x, box_y, box_w, box_h, 6, 6)

    # Draw camera/gift icon lines
    painter.setPen(QPen(icon_col, 1 if width < 60 else 2))
    scale_fac = width / 180.0
    r_outer = max(6, int(14 * scale_fac))
    r_inner = max(3, int(6 * scale_fac))
    cx = box_x + box_w // 2
    cy = box_y + box_h // 2
    painter.drawEllipse(cx - r_outer, cy - r_outer, r_outer * 2, r_outer * 2)
    painter.drawEllipse(cx - r_inner, cy - r_inner, r_inner * 2, r_inner * 2)

    if height > 80:
        # Title
        font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(title_col)
        painter.drawText(0, box_y + box_h + 16, width, 20, Qt.AlignmentFlag.AlignCenter, title)

        # Subtitle
        font_sub = QFont("Segoe UI", 8)
        painter.setFont(font_sub)
        painter.setPen(sub_col)
        painter.drawText(0, box_y + box_h + 36, width, 18, Qt.AlignmentFlag.AlignCenter, subtitle)

    painter.end()
    return pixmap
