# Modern Dark/Light Theme Mix for Thangam Stores

GLOBAL_STYLE = """
QMainWindow, QDialog {
    background-color: #f5f6fa;
}

QTabWidget::pane {
    border: 1px solid #dcdde1;
    background-color: white;
    border-radius: 5px;
}

QTabBar::tab {
    background-color: #e1e2e6;
    color: #2f3640;
    padding: 8px 12px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: white;
    font-weight: bold;
}

* {
    font-family: 'Segoe UI', sans-serif;
    font-size: 14px;
    color: #2f3640;
}

/* Menu Bar */
QMenuBar {
    background-color: #f5f6fa;
    color: #2f3640;
}
QMenuBar::item:selected {
    background-color: #dcdde1;
}
QMenu {
    background-color: white;
    color: #2f3640;
    border: 1px solid #dcdde1;
}
QMenu::item:selected {
    background-color: #0097e6;
    color: white;
}

/* Inputs */
QLineEdit, QComboBox, QDateEdit {
    padding: 8px;
    border: 1px solid #dcdde1;
    border-radius: 5px;
    background-color: white;
    selection-background-color: #00a8ff;
}

QLineEdit:focus, QComboBox:focus, QDateEdit:focus {
    border: 1px solid #00a8ff;
}

QAbstractItemView {
    background-color: white;
    color: #2f3640;
    selection-background-color: #dff9fb;
    selection-color: #2f3640;
    border: 1px solid #dcdde1;
}

/* Buttons */
QPushButton {
    background-color: #0097e6;
    color: white;
    padding: 8px 16px;
    border-radius: 5px;
    border: none;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #00a8ff;
}

QPushButton:pressed {
    background-color: #0084c7;
}

/* Primary Action Button (e.g. Print) */
QPushButton#primaryBtn {
    background-color: #0097e6;
    font-size: 16px;
    padding: 12px;
}

QPushButton#primaryBtn:hover {
    background-color: #00a8ff;
}

/* Danger Button (e.g. Clear) */
QPushButton#dangerBtn {
    background-color: #e84118;
}

QPushButton#dangerBtn:hover {
    background-color: #c23616;
}

/* Tables */
QTableWidget {
    background-color: white;
    border: 1px solid #dcdde1;
    gridline-color: #f5f6fa;
    selection-background-color: #dff9fb;
    selection-color: #2f3640;
}

QHeaderView::section {
    background-color: #0097e6;
    color: white;
    padding: 8px;
    border: none;
    font-weight: bold;
}

/* Sidebar / Panels */
QListWidget {
    background-color: white;
    border: 1px solid #dcdde1;
    border-radius: 5px;
}

QGroupBox {
    font-weight: bold;
    border: 1px solid #dcdde1;
    border-radius: 5px;
    margin-top: 10px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}

#totalsFrame {
    background-color: white;
    border-radius: 10px;
    border: 1px solid #dcdde1;
}

#lblGrandTotal {
    font-size: 32px;
    font-weight: bold;
    color: #27ae60;
    padding: 10px;
    background-color: #eafaf1;
    border-radius: 8px;
    border: 1px solid #abebc6;
}

#sectionHeader {
    font-size: 18px;
    font-weight: bold;
    color: #2c3e50;
    margin-bottom: 5px;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #f1f2f6;
    width: 10px;
    margin: 0px 0px 0px 0px;
}
QScrollBar::handle:vertical {
    background: #ced6e0;
    min-height: 20px;
    border-radius: 5px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    border: none;
    background: #f1f2f6;
    height: 10px;
    margin: 0px 0px 0px 0px;
}
QScrollBar::handle:horizontal {
    background: #ced6e0;
    min-width: 20px;
    border-radius: 5px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
/* Custom Component Selectors */
QLineEdit#prodSearch {
    padding: 6px 12px;
    font-size: 13px;
    border: 2px solid #2196F3;
    border-radius: 6px;
    background-color: #ffffff;
    color: #2f3640;
    selection-background-color: #00a8ff;
}
QLineEdit#prodSearch:focus {
    border: 2px solid #2e7d32;
    background-color: #fcfffd;
}

QLabel#lblCust {
    font-weight: bold;
    color: #555555;
}

QPushButton#debtBtn {
    background-color: #ffebee;
    color: #c62828;
    border: 1px solid #ffcdd2;
}
QPushButton#debtBtn:hover {
    background-color: #ffcdd2;
}

QPushButton#resumeBtn {
    background-color: #2196F3;
    color: white;
}
QPushButton#resumeBtn:hover {
    background-color: #1e88e5;
}

QPushButton#holdBtn {
    background-color: #FFC107;
    color: #212121;
}
QPushButton#holdBtn:hover {
    background-color: #ffb300;
}
"""

# Specific styles for labels
TOTAL_LABEL_STYLE = """
QLabel {
    font-size: 32px;
    font-weight: bold;
    color: #27ae60;
    padding: 10px;
    background-color: #eafaf1;
    border-radius: 8px;
    border: 1px solid #abebc6;
}
"""

SECTION_HEADER_STYLE = """
QLabel {
    font-size: 18px;
    font-weight: bold;
    color: #2c3e50;
    margin-bottom: 5px;
}
"""

DARK_THEME = """
QMainWindow, QDialog {
    background-color: #2f3640;
}

QTabWidget::pane {
    border: 1px solid #7f8fa6;
    background-color: #353b48;
    border-radius: 5px;
}

QTabBar::tab {
    background-color: #2f3640;
    color: #f5f6fa;
    padding: 8px 12px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
    border: 1px solid #7f8fa6;
    border-bottom: none;
}

QTabBar::tab:selected {
    background-color: #353b48;
    font-weight: bold;
    border-bottom: 1px solid #353b48; /* Match pane background */
}

* {
    font-family: 'Segoe UI', sans-serif;
    font-size: 14px;
    color: #f5f6fa;
}

/* Menu Bar */
QMenuBar {
    background-color: #2f3640;
    color: #f5f6fa;
}
QMenuBar::item:selected {
    background-color: #353b48;
}
QMenu {
    background-color: #353b48;
    color: #f5f6fa;
    border: 1px solid #7f8fa6;
}
QMenu::item:selected {
    background-color: #0097e6;
    color: white;
}

/* Inputs */
QLineEdit, QComboBox, QDateEdit {
    padding: 8px;
    border: 1px solid #7f8fa6;
    border-radius: 5px;
    background-color: #353b48;
    color: white;
    selection-background-color: #00a8ff;
    placeholder-text-color: #8892a0;
}

QLineEdit:focus, QComboBox:focus, QDateEdit:focus {
    border: 1px solid #00a8ff;
}

QAbstractItemView {
    background-color: #353b48;
    color: white;
    selection-background-color: #00a8ff;
    selection-color: white;
    border: 1px solid #7f8fa6;
}

/* Buttons */
QPushButton {
    background-color: #4b5563;
    color: white;
    padding: 8px 16px;
    border-radius: 5px;
    border: none;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #606f84;
}

QPushButton:pressed {
    background-color: #2f3640;
}

/* Primary Action Button */
QPushButton#primaryBtn {
    background-color: #0097e6;
}

QPushButton#primaryBtn:hover {
    background-color: #00a8ff;
}

/* Danger Button */
QPushButton#dangerBtn {
    background-color: #e84118;
}

QPushButton#dangerBtn:hover {
    background-color: #c23616;
}

/* Tables */
QTableWidget {
    background-color: #353b48;
    border: 1px solid #7f8fa6;
    gridline-color: #2f3640;
    selection-background-color: #00a8ff;
    selection-color: white;
    color: white;
    alternate-background-color: #2d323d;
}

QHeaderView::section {
    background-color: #272d36;
    color: white;
    padding: 8px;
    border: none;
    font-weight: bold;
}

/* Sidebar / Panels */
QListWidget {
    background-color: #353b48;
    border: 1px solid #7f8fa6;
    border-radius: 5px;
    color: white;
}

QListWidget::item:hover {
    background-color: #404856;
}

QListWidget::item:selected {
    background-color: #0097e6;
    color: white;
}

QGroupBox {
    font-weight: bold;
    border: 1px solid #7f8fa6;
    border-radius: 5px;
    margin-top: 10px;
    color: #f5f6fa;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    color: #f5f6fa;
}

#totalsFrame {
    background-color: #353b48;
    border-radius: 10px;
    border: 1px solid #7f8fa6;
}

#lblGrandTotal {
    font-size: 32px;
    font-weight: bold;
    color: #2ecc71;
    padding: 10px;
    background-color: #272d36;
    border-radius: 8px;
    border: 1px solid #27ae60;
}

#sectionHeader {
    font-size: 18px;
    font-weight: bold;
    color: #f5f6fa;
    margin-bottom: 5px;
}

/* Custom Component Selectors - Dark Mode */
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

QLabel#lblCust {
    font-weight: bold;
    color: #dcdde1;
}

QPushButton#debtBtn {
    background-color: #4a2328;
    color: #ffb4b4;
    border: 1px solid #78353d;
}
QPushButton#debtBtn:hover {
    background-color: #5c2b32;
}

QPushButton#resumeBtn {
    background-color: #1976d2;
    color: white;
}
QPushButton#resumeBtn:hover {
    background-color: #2196f3;
}

QPushButton#holdBtn {
    background-color: #f39c12;
    color: #1a1a1a;
    font-weight: bold;
}
QPushButton#holdBtn:hover {
    background-color: #e67e22;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #272d36;
    width: 10px;
    margin: 0px 0px 0px 0px;
}
QScrollBar::handle:vertical {
    background: #576574;
    min-height: 20px;
    border-radius: 5px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    border: none;
    background: #272d36;
    height: 10px;
    margin: 0px 0px 0px 0px;
}
QScrollBar::handle:horizontal {
    background: #576574;
    min-width: 20px;
    border-radius: 5px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
"""


TOUCH_STYLE = """
/* Touch Mode Enhancements */
* {
    font-size: 18px;
}

QPushButton {
    padding: 15px 25px;
    border-radius: 8px;
    font-size: 18px;
}

QTableWidget {
    font-size: 18px;
}

QHeaderView::section {
    padding: 12px;
    font-size: 18px;
}

QLineEdit, QComboBox, QDateEdit {
    padding: 12px;
    font-size: 18px;
}

QTabBar::tab {
    padding: 15px 25px;
    font-size: 18px;
}

QListWidget {
    font-size: 18px;
}

QListWidget::item {
    padding: 10px;
}

/* Larger scrollbars for touch */
QScrollBar:vertical {
    width: 25px;
}

QScrollBar::handle:vertical {
    min-height: 40px;
}

QScrollBar:horizontal {
    height: 25px;
}

QScrollBar::handle:horizontal {
    min-width: 40px;
}
"""

from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt

def get_theme_palette(theme_name):
    if theme_name == 'Dark':
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(47, 54, 64))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(245, 246, 250))
        palette.setColor(QPalette.ColorRole.Base, QColor(44, 50, 61))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 59, 72))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(245, 246, 250))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(47, 54, 64))
        palette.setColor(QPalette.ColorRole.Text, QColor(245, 246, 250))
        palette.setColor(QPalette.ColorRole.Button, QColor(75, 85, 99))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(245, 246, 250))
        palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        palette.setColor(QPalette.ColorRole.Link, QColor(0, 151, 230))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 168, 255))
        palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(136, 146, 160))
        return palette
    else:
        return QPalette()

def get_theme_style(theme_name, touch_mode=False):
    style = GLOBAL_STYLE
    if theme_name == 'Dark':
        style = DARK_THEME
    
    if touch_mode:
        style += TOUCH_STYLE
        
    return style

def apply_theme_to_app(app, theme_name, touch_mode=False):
    """Applies stylesheet and palette uniformly across the QApplication."""
    if not app:
        return
    app.setStyleSheet(get_theme_style(theme_name, touch_mode))
    pal = get_theme_palette(theme_name)
    if pal:
        app.setPalette(pal)

