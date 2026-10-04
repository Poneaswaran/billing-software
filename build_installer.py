#!/usr/bin/env python3
"""
ToyPop POS & Billing - Master Installer Build Script
Compiles the application with PyInstaller and packages it into an Inno Setup Windows Installation Wizard.

Usage:
    python build_installer.py
    or:
    pipenv run python build_installer.py
"""

import os
import sys
import shutil
import subprocess
import time

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BASE_DIR, "dist")
BUILD_DIR = os.path.join(BASE_DIR, "build")
APP_DIST_DIR = os.path.join(DIST_DIR, "ToyPopBilling")
INSTALLER_DIST_DIR = os.path.join(DIST_DIR, "installer")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
ICON_PATH = os.path.join(ASSETS_DIR, "icon.ico")
ISS_SCRIPT = os.path.join(BASE_DIR, "installer", "setup.iss")


def print_step(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def ensure_assets():
    """Ensure icon and asset files exist."""
    print_step("Step 1: Validating Assets")
    os.makedirs(ASSETS_DIR, exist_ok=True)
    
    if not os.path.exists(ICON_PATH):
        # Look for favicon in public folder
        parent_favicon = os.path.abspath(os.path.join(BASE_DIR, "..", "public", "favicon.ico"))
        if os.path.exists(parent_favicon):
            print(f"[*] Copying icon from {parent_favicon} to {ICON_PATH}...")
            shutil.copy2(parent_favicon, ICON_PATH)
        else:
            print("[!] Warning: favicon.ico not found in parent directory.")
    else:
        print(f"[OK] Application icon found: {ICON_PATH}")


def find_iscc():
    """Find the Inno Setup Compiler (ISCC.exe)."""
    candidates = [
        shutil.which("iscc"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"),
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Inno Setup 7\ISCC.exe"),
        r"C:\Program Files (x86)\Inno Setup 7\ISCC.exe",
        r"C:\Program Files\Inno Setup 7\ISCC.exe",
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    return None


def ensure_iscc():
    """Locates or installs Inno Setup if missing."""
    print_step("Step 2: Checking Inno Setup Compiler")
    iscc = find_iscc()
    if iscc:
        print(f"[OK] Found Inno Setup Compiler: {iscc}")
        return iscc

    print("[!] Inno Setup compiler (ISCC.exe) not found on system PATH or default locations.")
    print("[*] Attempting to install Inno Setup via Windows Package Manager (winget)...")
    try:
        cmd = [
            "winget", "install", "--id", "JRSoftware.InnoSetup",
            "-e", "--silent", "--accept-source-agreements", "--accept-package-agreements"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if res.returncode == 0:
            print("[OK] Inno Setup successfully installed via winget!")
            time.sleep(2)
            iscc = find_iscc()
            if iscc:
                return iscc
    except Exception as e:
        print(f"[!] Winget auto-install failed: {e}")

    print("\n[ERROR] Inno Setup is required to build the Windows Installation Wizard.")
    print("Please install Inno Setup from: https://jrsoftware.org/isdl.php")
    print("Or run in terminal: winget install JRSoftware.InnoSetup\n")
    sys.exit(1)


def find_escpos_capabilities():
    """Find capabilities.json from python-escpos."""
    try:
        import escpos
        cap_file = os.path.join(os.path.dirname(escpos.__file__), "capabilities.json")
        if os.path.exists(cap_file):
            return cap_file
    except Exception:
        pass
    return None


def run_pyinstaller():
    """Build the application using PyInstaller into onedir format."""
    print_step("Step 3: Compiling Application with PyInstaller")
    
    # Locate capabilities.json
    cap_file = find_escpos_capabilities()
    if not cap_file:
        print("[!] Warning: escpos capabilities.json not found in python environment.")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--onedir",
        "--name", "ToyPopBilling",
        "--add-data", f"data{os.pathsep}data",
        "--add-data", f"app{os.pathsep}app",
    ]

    if os.path.exists(ASSETS_DIR):
        cmd.extend(["--add-data", f"assets{os.pathsep}assets"])

    if os.path.exists(ICON_PATH):
        cmd.extend(["--icon", ICON_PATH])

    if cap_file and os.path.exists(cap_file):
        cmd.extend(["--add-data", f"{cap_file}{os.pathsep}escpos"])

    # Hidden imports for reports and barcodes
    hidden_imports = [
        "reportlab.graphics.barcode.code93",
        "reportlab.graphics.barcode.code128",
        "reportlab.graphics.barcode.code39",
        "reportlab.graphics.barcode.usps",
        "reportlab.graphics.barcode.qr",
        "reportlab.graphics.barcode.common",
        "reportlab.graphics.barcode.usps4s",
        "reportlab.graphics.barcode.ecc200datamatrix",
        "app.single_instance",
        "app.utils.autostart",
    ]
    for h in hidden_imports:
        cmd.extend(["--hidden-import", h])

    cmd.append("run.py")

    print(f"[*] Running command:\n{' '.join(cmd)}\n")
    res = subprocess.run(cmd, cwd=BASE_DIR)
    if res.returncode != 0:
        print("[ERROR] PyInstaller compilation failed!")
        sys.exit(res.returncode)

    exe_path = os.path.join(APP_DIST_DIR, "ToyPopBilling.exe")
    if not os.path.exists(exe_path):
        print(f"[ERROR] Output executable not found at: {exe_path}")
        sys.exit(1)

    print(f"\n[OK] PyInstaller build succeeded! Output: {APP_DIST_DIR}")


def run_inno_setup(iscc_path):
    """Compile the Inno Setup script into a Windows Installation Wizard."""
    print_step("Step 4: Compiling Windows Installation Wizard with Inno Setup")
    os.makedirs(INSTALLER_DIST_DIR, exist_ok=True)

    cmd = [iscc_path, ISS_SCRIPT]
    print(f"[*] Running Inno Setup:\n{' '.join(cmd)}\n")
    res = subprocess.run(cmd, cwd=os.path.join(BASE_DIR, "installer"))
    if res.returncode != 0:
        print("[ERROR] Inno Setup compilation failed!")
        sys.exit(res.returncode)

    # Detect version from ISS script
    version = "1.0.1"
    try:
        with open(ISS_SCRIPT, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("#define MyAppVersion"):
                    version = line.split('"')[1]
                    break
    except Exception:
        pass

    installer_file = os.path.join(INSTALLER_DIST_DIR, f"ToyPopBilling_Setup_v{version}.exe")
    if not os.path.exists(installer_file):
        # Find any .exe in installer folder
        exes = [f for f in os.listdir(INSTALLER_DIST_DIR) if f.endswith(".exe")]
        if exes:
            installer_file = os.path.join(INSTALLER_DIST_DIR, exes[0])

    print_step("Step 5: Build Summary & Verification")
    if os.path.exists(installer_file):
        size_mb = os.path.getsize(installer_file) / (1024 * 1024)
        print(f"[SUCCESS] Windows Installation Wizard created successfully!")
        print(f" Location : {installer_file}")
        print(f" Size     : {size_mb:.2f} MB")
        print("\nWizard Highlights:")
        print("  - Installs ToyPop Billing into LocalAppData (No admin rights required)")
        print("  - Creates Desktop Shortcut & Start Menu Shortcut")
        print("  - Configures Background Service to start on Windows boot")
        print("  - Opens instantly in < 0.1s when user double-clicks desktop shortcut")
        print("  - Clean uninstaller available in Windows Settings -> Apps")
    else:
        print("[!] Warning: Installer file not found at expected location.")


def main():
    print("\n" + "#" * 70)
    print("  TOYPOP POS & BILLING - WINDOWS INSTALLER BUILD PIPELINE")
    print("#" * 70)

    start_time = time.time()
    ensure_assets()
    iscc_path = ensure_iscc()
    run_pyinstaller()
    run_inno_setup(iscc_path)

    elapsed = time.time() - start_time
    print(f"\n[DONE] Pipeline completed in {elapsed:.1f} seconds.\n")


if __name__ == "__main__":
    main()
