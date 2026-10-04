# Thangam Billing Software 🏪

A robust, easy-to-use Point of Sale (POS) and billing application built with **Python** and **PyQt6**, designed for **Thangam Stores** and similar small to medium-sized retail businesses.

> **Note:** Originally built to assist my dad's store, this software emphasizes speed, simplicity, and reliability.

## ✨ Features

### ⚡ Fast Billing
- **Smart Search**: Quickly find products by name or code (shortcuts supported).
- **Barcode Support**: Seamless integration with USB/Serial barcode scanners.
- **Cart Management**: Hold/Resume bills, clear cart, and edit quantities on the fly.
- **Multiple Payment Modes**: Cash, UPI, Card, and Debt tracking.

### 📊 Dashboard & Analytics
- **Visual Insights**: View sales trends, top-selling products, and payment method distribution charts.
- **Reports**: Generate detailed sales reports by date range.
- **Excel Export**: Export reports to `.xlsx` for further analysis.

### 👥 Customer & Debt Management
- **Customer Database**: Store client details and associate them with bills.
- **Debt Tracking**: Manage pending payments and debt customers.

### 🎨 Modern & Responsive UI
- **Touch Mode**: Specialized mode with larger buttons and fonts for touch-screen monitors.
- **Theming**: Toggle between Light and Dark themes.
- **Keyboard Shortcuts**: Designed for power users (F1: Search, F2: Qty, F3: Discount, F12: Print).

### 🖨️ Versatile Printing
- **Format Support**: Thermal Receipt (80mm/58mm) and PDF generation.
- **Branding**: Customizable Shop Logo and Header Message on receipts.
- **Hardware Agnostic**: Works with Windows Drivers, Direct USB, Serial, or Network printers.

## 🛠️ Tech Stack

- **Language**: Python 3.10+
- **GUI**: PyQt6
- **Database**: SQLAlchemy (SQLite)
- **Analytics**: Matplotlib, Pandas
- **Printing**: python-escpos, ReportLab

## 🚀 Getting Started

### Prerequisites
- Python 3.10 or higher.
- Git.

### Installation

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/poneaswaran/billing-software
    cd thangam-billing
    ```

2.  **Create a Virtual Environment**
    ```bash
    python -m venv .venv
    # Windows
    .venv\Scripts\activate
    # macOS/Linux
    source .venv/bin/activate
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

### Running the Application

To start the billing software:

```bash
python run.py
```

## ⌨️ Keyboard Shortcuts

| Key | Action |
| :--- | :--- |
| **F1** | Focus Customer Search |
| **F2** | Focus Quantity Field |
| **F3** | Focus Discount Field |
| **F12** | Complete & Print Bill |
| **Enter** | Add Product / Confirm |

## 📦 Building for Windows & Installation Wizard

To build the complete **Windows Installation Wizard** (`ToyPopBilling_Setup_v1.0.3.exe`):

```bash
# Option 1: Using the master build script (recommended)
python build_installer.py

# Option 2: Using the one-click Windows batch file
build.bat

```

### ⚡ Background Service & Instant Launch Architecture
- **Auto-Start on Boot**: When the computer starts, ToyPop Billing initializes in the background (`--background`) and resides silently in memory (0% CPU, ~70MB RAM).
- **Instant Open**: When the user double-clicks the desktop shortcut, an ultra-fast IPC signal wakes up the pre-warmed instance in **< 50 milliseconds**, completely skipping cold-start delays.
- **System Tray**: Right-click the tray icon near the clock for quick catalog sync, settings, or complete exit.
- **Minimize to Tray**: Closing the window with `[X]` keeps the engine pre-warmed for instant access throughout the workday.

### 🛠️ Manual PyInstaller Build (Portable Only)
If you only need a raw portable build without an installer wizard:
```bash
pyinstaller --noconfirm --onedir --windowed \
    --name "ToyPopBilling" \
    --icon "assets/icon.ico" \
    --add-data "data;data" \
    --add-data "app;app" \
    --add-data "assets;assets" \
    run.py
```

## 🤝 Contributing

Contributions are welcome! Fork the repo, create a branch, and submit a PR.

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---
*Built with ❤️ by Poneaswaran*
