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
    background-color: #718093;
    color: white;
    padding: 8px 16px;
    border-radius: 5px;
    border: none;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #7f8fa6;
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
}

QHeaderView::section {
    background-color: #2f3640;
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

QFrame {
    background-color: #353b48;
    border: 1px solid #7f8fa6;
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
    background-color: #2f3640;
    border-radius: 8px;
    border: 1px solid #27ae60;
}

#sectionHeader {
    font-size: 18px;
    font-weight: bold;
    color: #f5f6fa;
    margin-bottom: 5px;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #2f3640;
    width: 10px;
    margin: 0px 0px 0px 0px;
}
QScrollBar::handle:vertical {
    background: #7f8fa6;
    min-height: 20px;
    border-radius: 5px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    border: none;
    background: #2f3640;
    height: 10px;
    margin: 0px 0px 0px 0px;
}
QScrollBar::handle:horizontal {
    background: #7f8fa6;
    min-width: 20px;
    border-radius: 5px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
"""

def get_theme_style(theme_name):
    if theme_name == 'Dark':
        return DARK_THEME
    return GLOBAL_STYLE
