# Thangam Billing Software 🏪

A robust, easy-to-use Point of Sale (POS) and billing application built with Python and PyQt6. 

**Note:** This project holds a special place in my heart as I originally built it to help my dad manage his store, "Thangam Stores". It is designed to be simple, fast, and reliable for small to medium-sized retail businesses.

## ✨ Features

*   **⚡ Fast Billing**:
    *   Quick product search and addition to cart.
    *   Barcode scanner support for rapid checkout.
    *   Automatic tax and discount calculations.
    *   Multiple payment modes (Cash, UPI, Card, Debt.).
*   **📦 Product Management**:
    *   Add, edit, and delete products easily.
    *   Manage inventory and stock levels.
    *   Support for different units of measurement.
*   **👥 Customer Management**:
    *   Maintain a customer database.
    *   Quickly search and associate customers with bills.
*   **🖨️ Versatile Printing**:
    *   Support for Thermal Printers (USB, Serial, Network).
    *   Customizable receipt formats.
    *   Generates PDF reports using ReportLab.
*   **📊 Reports & Analytics**:
    *   View daily sales reports.
    *   Export sales data for analysis.
*   **⚙️ Configurable**:
    *   Customize store details (Name, Address, Phone).
    *   Configure printer settings directly from the app.
*   **🎨 Modern UI**:
    *   Clean and intuitive interface built with PyQt6.
    *   Dark/Light mode support (if applicable, otherwise just "Clean Interface").

## 🛠️ Tech Stack

*   **Language**: Python 3.10+
*   **GUI Framework**: PyQt6
*   **Database**: SQLite (Lightweight and serverless)
*   **Printing**: python-escpos
*   **Reporting**: ReportLab
*   **Packaging**: PyInstaller

## 🚀 Getting Started

### Prerequisites

*   Python 3.10 or higher installed on your system.
*   Git (to clone the repository).

### Installation

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/yourusername/thangam-billing.git
    cd thangam-billing
    ```

2.  **Create a Virtual Environment (Recommended)**
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

To start the billing software, simply run:

```bash
python run.py
```

## 📦 Building for Windows

If you want to create a standalone `.exe` file to run on machines without Python installed:

```bash
pyinstaller --noconfirm --onefile --windowed --add-data "data;data" --add-data "app;app" --name "ThangamBilling" run.py
```

The executable will be generated in the `dist/` folder.

## 🤝 Contributing

Contributions are welcome! If you have ideas to make this better (or if you want to use it for your own family business), feel free to fork the repo and submit a pull request.

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

## 🙏 Acknowledgements

*   **My Dad**: For being the inspiration and the first user of this software.
*   **Open Source Community**: For the amazing libraries that made this possible.

---
*Built with ❤️ by Poneaswaran*
