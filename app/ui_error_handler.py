from PyQt6.QtWidgets import QMessageBox

def show_error(parent, title, message, detailed_text=None):
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Icon.Critical)
    msg.setWindowTitle(title)
    msg.setText(message)
    if detailed_text:
        msg.setDetailedText(detailed_text)
    msg.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg.exec()

def show_warning(parent, title, message):
    QMessageBox.warning(parent, title, message)

def show_info(parent, title, message):
    QMessageBox.information(parent, title, message)

def ask_retry_ignore(parent, title, message):
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Icon.Warning)
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.setStandardButtons(QMessageBox.StandardButton.Retry | QMessageBox.StandardButton.Ignore)
    return msg.exec() == QMessageBox.StandardButton.Retry
