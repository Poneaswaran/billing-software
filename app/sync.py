import json
import urllib.request
import urllib.error
from datetime import datetime
from sqlalchemy import text
from app.db import get_db, init_db, DB_PATH
from app.orm_models import Product, Bill, BillItem
from app.models import SettingsModel

try:
    from PyQt6.QtCore import QThread, pyqtSignal
    HAS_PYQT = True
except ImportError:
    HAS_PYQT = False


def ensure_db_columns():
    """Safely adds cloud sync columns to SQLite tables if they do not exist."""
    init_db()
    session = get_db()
    try:
        engine = session.get_bind()
        with engine.connect() as conn:
            # Check products columns
            res = conn.execute(text("PRAGMA table_info(products)")).fetchall()
            existing_product_cols = [r[1] for r in res]
            
            if 'cloud_id' not in existing_product_cols:
                conn.execute(text("ALTER TABLE products ADD COLUMN cloud_id VARCHAR"))
            if 'stock_qty' not in existing_product_cols:
                conn.execute(text("ALTER TABLE products ADD COLUMN stock_qty INTEGER DEFAULT 0"))
            if 'gst_rate_bps' not in existing_product_cols:
                conn.execute(text("ALTER TABLE products ADD COLUMN gst_rate_bps INTEGER DEFAULT 1800"))
            if 'hsn_code' not in existing_product_cols:
                conn.execute(text("ALTER TABLE products ADD COLUMN hsn_code VARCHAR"))
            if 'image_url' not in existing_product_cols:
                conn.execute(text("ALTER TABLE products ADD COLUMN image_url VARCHAR"))
                
            # Check bills columns
            res_bills = conn.execute(text("PRAGMA table_info(bills)")).fetchall()
            existing_bill_cols = [r[1] for r in res_bills]
            
            if 'synced' not in existing_bill_cols:
                conn.execute(text("ALTER TABLE bills ADD COLUMN synced INTEGER DEFAULT 0"))
            if 'cloud_order_id' not in existing_bill_cols:
                conn.execute(text("ALTER TABLE bills ADD COLUMN cloud_order_id VARCHAR"))
            if 'local_bill_id' not in existing_bill_cols:
                conn.execute(text("ALTER TABLE bills ADD COLUMN local_bill_id VARCHAR"))
                
            conn.commit()
    except Exception as e:
        print(f"[Sync] DB migration notice: {e}")
    finally:
        session.close()


class ToyPopSyncClient:
    """Client for synchronizing the desktop offline billing software with ToyPop Cloud."""

    DEFAULT_URL = "http://localhost:3000"
    DEFAULT_KEY = "tppos_live_toypop_pos_terminal_secret_2026"
    DEFAULT_TERMINAL = "CHENNAI-POS-01"

    def __init__(self, base_url=None, api_key=None, terminal_id=None):
        ensure_db_columns()
        self.base_url = (
            base_url
            or SettingsModel.get_setting("cloud_api_url", self.DEFAULT_URL)
        ).rstrip("/")
        self.api_key = (
            api_key
            or SettingsModel.get_setting("cloud_api_key", self.DEFAULT_KEY)
        )
        self.terminal_id = (
            terminal_id
            or SettingsModel.get_setting("cloud_terminal_id", self.DEFAULT_TERMINAL)
        )

    def _make_request(self, endpoint, method="GET", data=None):
        url = f"{self.base_url}{endpoint}"
        headers = {
            "x-pos-api-key": self.api_key,
            "x-terminal-id": self.terminal_id,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "ToyPop-Billing-Terminal/1.0",
        }

        body_bytes = None
        if data is not None:
            body_bytes = json.dumps(data).encode("utf-8")

        req = urllib.request.Request(url, data=body_bytes, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=12) as response:
                status = response.getcode()
                raw = response.read().decode("utf-8")
                return {"status": status, "data": json.loads(raw)}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            try:
                parsed_err = json.loads(err_body)
            except Exception:
                parsed_err = {"error": err_body}
            return {"status": e.code, "error": parsed_err}
        except Exception as e:
            return {"status": 0, "error": str(e)}

    def is_connected(self):
        """Quick check to see if ToyPop Cloud is reachable and responsive."""
        try:
            res = self._make_request("/api/pos/bootstrap")
            return res.get("status") == 200
        except Exception:
            return False

    def bootstrap(self):
        """Fetches terminal configuration, store info, and tax rules from ToyPop."""
        res = self._make_request("/api/pos/bootstrap")
        if res.get("status") == 200:
            store = res["data"].get("store", {})
            # Update local store profile settings automatically
            if store.get("name"):
                SettingsModel.set_setting("store_name", store["name"])
            if store.get("phone"):
                SettingsModel.set_setting("store_phone", store["phone"])
            if store.get("gstin"):
                SettingsModel.set_setting("store_gstin", store["gstin"])
            return {"success": True, "data": res["data"]}
        return {"success": False, "error": res.get("error", "Failed to connect")}

    def sync_catalog(self, limit=200):
        """Downloads updated products and stock counts from ToyPop and updates local SQLite."""
        endpoint = f"/api/pos/catalog?limit={limit}"
        res = self._make_request(endpoint)
        if res.get("status") != 200:
            return {"success": False, "error": res.get("error", "Catalog request failed")}

        items = res["data"].get("items", [])
        session = get_db()
        synced_count = 0
        new_count = 0

        try:
            for item in items:
                cloud_id = item.get("id")
                name = item.get("name")
                code = item.get("barcode") or item.get("sku") or str(cloud_id)
                price = float(item.get("priceRupees", (item.get("pricePaise", 0) / 100.0)))
                category = item.get("category", "General")
                stock = int(item.get("stock", 0))
                gst_bps = int(item.get("gstRateBps", 1800))
                hsn = str(item.get("hsnCode", "95030090"))
                image_url = str(item.get("imageUrl") or item.get("image") or "")

                # Try matching existing product by cloud_id or barcode/code
                prod = session.query(Product).filter(
                    (Product.cloud_id == cloud_id) | (Product.code == code)
                ).first()

                if prod:
                    prod.name = name
                    prod.code = code
                    prod.price_per_unit = price
                    prod.category = category
                    prod.stock_qty = stock
                    prod.gst_rate_bps = gst_bps
                    prod.hsn_code = hsn
                    prod.cloud_id = cloud_id
                    if image_url:
                        prod.image_url = image_url
                    synced_count += 1
                else:
                    new_prod = Product(
                        name=name,
                        code=code,
                        base_unit="Pieces",
                        price_per_unit=price,
                        category=category,
                        stock_qty=stock,
                        gst_rate_bps=gst_bps,
                        hsn_code=hsn,
                        cloud_id=cloud_id,
                        image_url=image_url
                    )
                    session.add(new_prod)
                    new_count += 1

            session.commit()
            today_str = datetime.now().strftime("%Y-%m-%d")
            time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            SettingsModel.set_setting("last_catalog_sync_date", today_str)
            SettingsModel.set_setting("last_catalog_sync_time", time_str)
            return {
                "success": True,
                "synced": synced_count,
                "created": new_count,
                "total": len(items)
            }
        except Exception as e:
            session.rollback()
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    def is_first_time_sync(self) -> bool:
        """Returns True if local products database has 0 products or has never been synced."""
        session = get_db()
        try:
            prod_count = session.query(Product).count()
            last_date = SettingsModel.get_setting("last_catalog_sync_date", "")
            return prod_count == 0 or not last_date
        finally:
            session.close()

    def is_daily_sync_needed(self) -> bool:
        """Returns True if local DB is empty or has not been synced today."""
        if self.is_first_time_sync():
            return True
        last_date = SettingsModel.get_setting("last_catalog_sync_date", "")
        today = datetime.now().strftime("%Y-%m-%d")
        return last_date != today

    def sync_pending_bills(self):
        """Pushes locally completed offline bills to ToyPop Cloud orders collection."""
        session = get_db()
        try:
            unsynced = session.query(Bill).filter(
                (Bill.synced == 0) | (Bill.synced == None)
            ).all()

            if not unsynced:
                return {"success": True, "count": 0, "message": "No pending bills to sync"}

            synced_bills = 0
            errors = []

            for bill in unsynced:
                # Build items payload
                items_payload = []
                for bi in bill.items:
                    items_payload.append({
                        "productId": bi.product.cloud_id if bi.product and bi.product.cloud_id else f"local_{bi.product_id}",
                        "name": bi.product_name,
                        "sku": bi.product.code if bi.product and bi.product.code else str(bi.product_id),
                        "quantity": int(bi.quantity),
                        "unitPricePaise": int(round(bi.price * 100)),
                        "mrpPaise": int(round(bi.price * 100)),
                        "discountPaise": 0,
                        "gstRateBps": getattr(bi.product, 'gst_rate_bps', 1800) if bi.product else 1800,
                        "hsnCode": getattr(bi.product, 'hsn_code', '95030090') if bi.product else "95030090"
                    })

                method = (bill.payment_method or "Cash").lower()
                clean_method = "cash" if "cash" in method else ("upi" if "upi" in method else "card")

                payload = {
                    "localBillId": f"BILL-{bill.id}-{bill.bill_number}",
                    "billNumber": bill.bill_number,
                    "terminalId": self.terminal_id,
                    "paymentMethod": clean_method,
                    "paymentStatus": "paid",
                    "customer": {
                        "name": bill.customer.name if bill.customer else "Walk-in Customer",
                        "phone": bill.customer.phone if bill.customer else None
                    },
                    "items": items_payload,
                    "subtotalPaise": int(round(bill.subtotal * 100)),
                    "discountPaise": int(round((bill.discount_amount or 0) * 100)),
                    "taxPaise": int(round((bill.tax_amount or 0) * 100)),
                    "totalPaise": int(round(bill.grand_total * 100)),
                    "notes": f"Synchronized from Terminal {self.terminal_id}"
                }

                res = self._make_request("/api/pos/orders", method="POST", data=payload)
                if res.get("status") in (200, 201) and res.get("data", {}).get("success"):
                    bill.synced = 1
                    bill.cloud_order_id = res["data"].get("orderId")
                    bill.local_bill_id = payload["localBillId"]
                    synced_bills += 1
                else:
                    err_msg = res.get("error", "Unknown ingestion error")
                    errors.append(f"Bill {bill.bill_number}: {err_msg}")

            session.commit()
            return {
                "success": len(errors) == 0,
                "synced_bills": synced_bills,
                "pending": len(unsynced) - synced_bills,
                "errors": errors
            }
        except Exception as e:
            session.rollback()
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    def full_sync(self):
        """Executes full catalog download and offline bill upload."""
        cat_res = self.sync_catalog()
        bill_res = self.sync_pending_bills()
        return {
            "success": cat_res.get("success", False) and bill_res.get("success", False),
            "catalog": cat_res,
            "bills": bill_res,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }


if HAS_PYQT:
    class SyncWorker(QThread):
        """Background QThread for non-blocking POS Cloud Synchronization."""
        progress = pyqtSignal(str)
        finished = pyqtSignal(dict)
        error = pyqtSignal(str)

        def __init__(self, mode="full", parent=None):
            super().__init__(parent)
            self.mode = mode
            self.client = ToyPopSyncClient()

        def run(self):
            try:
                self.progress.emit("Connecting to ToyPop Cloud...")
                if self.mode == "bootstrap":
                    res = self.client.bootstrap()
                elif self.mode == "catalog":
                    self.progress.emit("Downloading updated product catalog...")
                    res = self.client.sync_catalog()
                elif self.mode == "bills":
                    self.progress.emit("Uploading offline retail bills...")
                    res = self.client.sync_pending_bills()
                else:
                    self.progress.emit("Synchronizing catalog & uploading bills...")
                    res = self.client.full_sync()

                if res.get("success"):
                    self.finished.emit(res)
                else:
                    self.error.emit(str(res.get("error", "Sync failed")))
            except Exception as e:
                self.error.emit(str(e))

    class CloudConnectionChecker(QThread):
        """Asynchronously probes ToyPop Cloud connectivity without freezing the UI."""
        status_checked = pyqtSignal(bool, dict)

        def __init__(self, client=None, parent=None):
            super().__init__(parent)
            self.client = client

        def run(self):
            try:
                c = self.client or ToyPopSyncClient()
                res = c.bootstrap()
                if res.get("success"):
                    self.status_checked.emit(True, res.get("data", {}))
                else:
                    self.status_checked.emit(False, {})
            except Exception:
                self.status_checked.emit(False, {})

    class DailyCatalogSyncWorker(QThread):
        """Background thread that automatically downloads/updates catalog if first time or daily update needed."""
        sync_started = pyqtSignal(str)
        sync_completed = pyqtSignal(bool, dict)

        def __init__(self, parent=None):
            super().__init__(parent)
            self.client = ToyPopSyncClient()

        def run(self):
            try:
                if not self.client.is_connected():
                    self.sync_completed.emit(False, {"skipped": True, "reason": "offline"})
                    return

                is_first = self.client.is_first_time_sync()
                is_daily = self.client.is_daily_sync_needed()

                if is_first:
                    self.sync_started.emit("First time setup: downloading product catalog from ToyPop Cloud...")
                    res = self.client.sync_catalog(limit=250)
                    res["is_first_time"] = True
                    self.sync_completed.emit(res.get("success", False), res)
                elif is_daily:
                    self.sync_started.emit("Daily update: synchronizing product catalog with ToyPop Cloud...")
                    res = self.client.sync_catalog(limit=250)
                    res["is_daily"] = True
                    self.sync_completed.emit(res.get("success", False), res)
                else:
                    self.sync_completed.emit(False, {"skipped": True, "reason": "already_synced_today"})
            except Exception as e:
                self.sync_completed.emit(False, {"error": str(e)})

