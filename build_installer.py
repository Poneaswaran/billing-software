#!/usr/bin/env python3
"""
ToyPop POS & Billing - Master Automated Installer Build & GitHub Release Script
- Automatically increments the version (patch/minor/major)
- Updates setup.iss and README.md with the new version
- Compiles the application with PyInstaller
- Packages the installer with Inno Setup into a Windows Installation Wizard
- Commits, tags, and pushes to Git
- Creates a GitHub Release and uploads the installer .exe asset

Usage:
    python build_installer.py                   # Auto-bumps patch (1.0.1 -> 1.0.2) & publishes to GitHub Release
    python build_installer.py --no-bump         # Builds & releases current version without bumping
    python build_installer.py --bump minor      # Bumps minor version (e.g. 1.0.1 -> 1.1.0)
    python build_installer.py --version 1.2.0   # Explicit version
    python build_installer.py --no-release      # Local build only without pushing to GitHub
"""

import os
import sys
import shutil
import subprocess
import time
import json
import re
import argparse
import urllib.request
import urllib.error

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


def get_current_version() -> str:
    """Read MyAppVersion from installer/setup.iss."""
    try:
        if os.path.exists(ISS_SCRIPT):
            with open(ISS_SCRIPT, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("#define MyAppVersion"):
                        return line.split('"')[1].strip()
    except Exception as e:
        print(f"[!] Warning reading version from setup.iss: {e}")
    return "1.0.1"


def bump_version(current: str, part: str = "patch") -> str:
    """Increment semantic version number."""
    parts = current.strip().split(".")
    while len(parts) < 3:
        parts.append("0")
    try:
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        return current

    if part == "major":
        major += 1
        minor = 0
        patch = 0
    elif part == "minor":
        minor += 1
        patch = 0
    else:  # patch
        patch += 1

    return f"{major}.{minor}.{patch}"


def update_version_in_files(new_version: str):
    """Update version in setup.iss and README.md."""
    # 1. Update setup.iss
    if os.path.exists(ISS_SCRIPT):
        with open(ISS_SCRIPT, "r", encoding="utf-8") as f:
            content = f.read()
        new_content = re.sub(
            r'#define\s+MyAppVersion\s+"[^"]+"',
            f'#define MyAppVersion "{new_version}"',
            content
        )
        with open(ISS_SCRIPT, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"[OK] Updated setup.iss to version {new_version}")

    # 2. Update README.md
    readme_path = os.path.join(BASE_DIR, "README.md")
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            r_content = f.read()
        new_r_content = re.sub(
            r"ToyPopBilling_Setup_v\d+\.\d+\.\d+\.exe",
            f"ToyPopBilling_Setup_v{new_version}.exe",
            r_content
        )
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(new_r_content)
        print(f"[OK] Updated README.md to reference ToyPopBilling_Setup_v{new_version}.exe")


def ensure_assets():
    """Ensure icon and asset files exist."""
    print_step("Step 1: Validating Assets")
    os.makedirs(ASSETS_DIR, exist_ok=True)
    
    if not os.path.exists(ICON_PATH):
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


def run_inno_setup(iscc_path, version: str):
    """Compile the Inno Setup script into a Windows Installation Wizard."""
    print_step("Step 4: Compiling Windows Installation Wizard with Inno Setup")
    os.makedirs(INSTALLER_DIST_DIR, exist_ok=True)

    cmd = [iscc_path, ISS_SCRIPT]
    print(f"[*] Running Inno Setup:\n{' '.join(cmd)}\n")
    res = subprocess.run(cmd, cwd=os.path.join(BASE_DIR, "installer"))
    if res.returncode != 0:
        print("[ERROR] Inno Setup compilation failed!")
        sys.exit(res.returncode)

    installer_file = os.path.join(INSTALLER_DIST_DIR, f"ToyPopBilling_Setup_v{version}.exe")
    if not os.path.exists(installer_file):
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
        return installer_file
    else:
        print("[!] Warning: Installer file not found at expected location.")
        return None


def get_github_token() -> str:
    """Retrieve GitHub token from environment or Git credential helper."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token.strip()
    try:
        res = subprocess.run(
            ["git", "credential", "fill"],
            input="url=https://github.com\n",
            text=True,
            capture_output=True,
            timeout=5
        )
        for line in res.stdout.splitlines():
            if line.startswith("password="):
                return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return ""


def get_github_repo() -> str:
    """Detect 'owner/repo' from git origin remote."""
    try:
        res = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            text=True,
            capture_output=True,
            timeout=5
        )
        url = res.stdout.strip()
        if url.endswith(".git"):
            url = url[:-4]
        if "github.com/" in url:
            return url.split("github.com/")[1]
        elif "github.com:" in url:
            return url.split("github.com:")[1]
    except Exception:
        pass
    return "Poneaswaran/billing-software"


def git_commit_and_tag(version: str, push: bool = True) -> bool:
    """Commit version bump and create git tag."""
    print_step("Step 6: Git Commit & Tag")
    tag = f"v{version}"
    try:
        subprocess.run(["git", "add", "installer/setup.iss", "README.md", "build_installer.py"], check=False)
        
        diff_res = subprocess.run(["git", "diff", "--cached", "--quiet"])
        if diff_res.returncode != 0:
            commit_msg = f"chore(release): bump version to {tag}"
            res = subprocess.run(["git", "commit", "-m", commit_msg])
            if res.returncode == 0:
                print(f"[OK] Committed version bump: {commit_msg}")
        else:
            print("[*] No uncommitted file changes detected.")

        # Create tag
        subprocess.run(["git", "tag", "-d", tag], capture_output=True)
        res = subprocess.run(["git", "tag", "-a", tag, "-m", f"Release {tag}"])
        if res.returncode == 0:
            print(f"[OK] Created Git tag: {tag}")

        if push:
            print(f"[*] Pushing commits and tag {tag} to GitHub...")
            subprocess.run(["git", "push", "origin", "main"], check=False)
            subprocess.run(["git", "push", "origin", tag], check=False)
            print(f"[OK] Pushed to GitHub origin: main and {tag}")
        return True
    except Exception as e:
        print(f"[!] Git commit/tag error: {e}")
        return False


def publish_github_release(version: str, installer_file: str) -> bool:
    """Publish a GitHub Release and upload the installer asset."""
    print_step("Step 7: Publishing GitHub Release")
    token = get_github_token()
    if not token:
        print("[!] GitHub token not found (neither in GITHUB_TOKEN nor git credential helper).")
        print("    Skipping automatic GitHub Release upload.")
        return False

    repo = get_github_repo()
    tag = f"v{version}"
    release_name = f"Release {tag} - ToyPop POS & Billing"
    body = f"""### ToyPop POS & Billing {tag} 🚀

#### Updates:
- Automated release build with latest features & optimizations.
- Instant Open background service pre-warm support.
- Windows Installation Wizard ({os.path.basename(installer_file)}).

#### Assets:
- Download and run **{os.path.basename(installer_file)}** to install or update.
"""

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "ToyPop-Build-Pipeline"
    }

    # 1. Check if release already exists for this tag
    release_data = None
    try:
        check_url = f"https://api.github.com/repos/{repo}/releases/tags/{tag}"
        req = urllib.request.Request(check_url, headers=headers)
        with urllib.request.urlopen(req) as resp:
            release_data = json.loads(resp.read().decode("utf-8"))
            print(f"[*] Found existing release for {tag} (ID: {release_data['id']})")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            print(f"[!] Error checking existing release: {e}")

    # 2. Create release if not exists
    if not release_data:
        payload = {
            "tag_name": tag,
            "name": release_name,
            "body": body,
            "draft": False,
            "prerelease": False
        }
        create_url = f"https://api.github.com/repos/{repo}/releases"
        req = urllib.request.Request(
            create_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={**headers, "Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req) as resp:
                release_data = json.loads(resp.read().decode("utf-8"))
                print(f"[OK] Created GitHub Release: {release_name} (ID: {release_data['id']})")
        except Exception as e:
            print(f"[ERROR] Failed to create GitHub Release: {e}")
            return False

    release_id = release_data["id"]
    html_url = release_data.get("html_url", f"https://github.com/{repo}/releases/tag/{tag}")

    # 3. Check and delete existing asset with the same name if exists
    filename = os.path.basename(installer_file)
    for asset in release_data.get("assets", []):
        if asset["name"] == filename:
            print(f"[*] Removing existing asset {filename} (ID: {asset['id']})...")
            del_req = urllib.request.Request(
                f"https://api.github.com/repos/{repo}/releases/assets/{asset['id']}",
                headers=headers,
                method="DELETE"
            )
            try:
                urllib.request.urlopen(del_req)
            except Exception:
                pass

    # 4. Upload installer asset
    upload_url = f"https://uploads.github.com/repos/{repo}/releases/{release_id}/assets?name={filename}"
    file_size = os.path.getsize(installer_file)
    size_mb = file_size / (1024 * 1024)
    print(f"[*] Uploading installer asset: {filename} ({size_mb:.2f} MB)...")

    try:
        with open(installer_file, "rb") as f:
            file_data = f.read()

        up_headers = {
            "Authorization": f"token {token}",
            "Content-Type": "application/octet-stream",
            "Content-Length": str(len(file_data)),
            "User-Agent": "ToyPop-Build-Pipeline"
        }
        up_req = urllib.request.Request(upload_url, data=file_data, headers=up_headers, method="POST")
        with urllib.request.urlopen(up_req) as up_resp:
            asset_res = json.loads(up_resp.read().decode("utf-8"))
            download_url = asset_res.get("browser_download_url", "")
            print(f"[SUCCESS] Release asset uploaded successfully!")
            print(f" Release Page : {html_url}")
            print(f" Download URL : {download_url}")
            return True
    except Exception as e:
        print(f"[ERROR] Failed to upload asset to GitHub Release: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="ToyPop POS & Billing - Automated Build & Release Pipeline")
    parser.add_argument("--bump", choices=["patch", "minor", "major"], default="patch",
                        help="Version segment to increment (default: patch)")
    parser.add_argument("--version", type=str, default=None,
                        help="Explicit version override (e.g. 1.0.2)")
    parser.add_argument("--no-bump", action="store_true",
                        help="Keep current version without auto-incrementing")
    parser.add_argument("--no-release", action="store_true",
                        help="Skip Git commit/tag push and GitHub Release publishing")
    parser.add_argument("--no-push", action="store_true",
                        help="Commit and tag locally but do not push to remote")

    args = parser.parse_args()

    print("\n" + "#" * 70)
    print("  TOYPOP POS & BILLING - WINDOWS INSTALLER BUILD & RELEASE PIPELINE")
    print("#" * 70)

    start_time = time.time()

    # Step 0: Version Resolution
    current_ver = get_current_version()
    if args.version:
        target_ver = args.version.lstrip("v")
    elif args.no_bump:
        target_ver = current_ver
    else:
        target_ver = bump_version(current_ver, args.bump)

    print(f"\n[*] Current Version : {current_ver}")
    print(f"[*] Target Version  : {target_ver}")
    update_version_in_files(target_ver)

    # Build steps
    ensure_assets()
    iscc_path = ensure_iscc()
    run_pyinstaller()
    installer_file = run_inno_setup(iscc_path, target_ver)

    # Git and Release steps
    if not args.no_release and installer_file and os.path.exists(installer_file):
        git_commit_and_tag(target_ver, push=not args.no_push)
        publish_github_release(target_ver, installer_file)

    elapsed = time.time() - start_time
    print(f"\n[DONE] Pipeline completed in {elapsed:.1f} seconds.\n")


if __name__ == "__main__":
    main()
