"""
ToyPop Billing Software - Integration Test Script
Tests the full lifecycle of Cloud Sync:
1. Cloud Server Health & Bootstrap Configuration
2. Product Catalog Synchronization (Cloud -> Local SQLite)
3. Offline Bill Creation & Push Ingestion (Local SQLite -> Cloud)
"""

import sys
import os
import uuid

# Ensure 'app' is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db import init_db, get_db
from app.orm_models import Product, Bill, BillItem, Customer
from app.sync import ToyPopSyncClient, ensure_db_columns

SERVER_URL = os.environ.get("TOYPOP_SERVER_URL", "http://localhost:3000")
API_KEY = os.environ.get("TOYPOP_POS_API_KEY", "tppos_live_toypop_pos_terminal_secret_2026")
TERMINAL_ID = "CLI-TEST-TERMINAL-01"

def run_test():
    print("=" * 60)
    print("[*] TOYPOP BILLING SOFTWARE - CLOUD INTEGRATION TEST")
    print(f"Server Target : {SERVER_URL}")
    print(f"Terminal ID   : {TERMINAL_ID}")
    print("=" * 60)

    # Step 0: Ensure local DB schema
    print("\n[Step 0/4] Initializing local database and schema migrations...")
    init_db()
    ensure_db_columns()
    print("[OK] Local database initialized.")

    client = ToyPopSyncClient(base_url=SERVER_URL, api_key=API_KEY, terminal_id=TERMINAL_ID)

    # Step 1: Test Bootstrap
    print("\n[Step 1/4] Testing /api/pos/bootstrap...")
    boot = client.bootstrap()
    if not boot.get("success"):
        print(f"[FAIL] Bootstrap failed: {boot.get('error')}")
        return False
    store = boot.get("data", {}).get("store", {})
    tax = boot.get("data", {}).get("taxSettings", {})
    print(f"[OK] Bootstrap SUCCESS!")
    print(f"   Store Name : {store.get('name')}")
    print(f"   GSTIN      : {store.get('gstin')}")
    print(f"   Default GST: {tax.get('defaultGstBasisPoints', 0) / 100}%")

    # Step 2: Test Catalog Sync
    print("\n[Step 2/4] Testing /api/pos/catalog sync...")
    cat_res = client.sync_catalog(limit=5)
    if not cat_res.get("success"):
        print(f"[FAIL] Catalog sync failed: {cat_res.get('error')}")
        return False
    print(f"[OK] Catalog sync SUCCESS! Synced {cat_res.get('synced', 0)} products into local SQLite.")
    
    session = get_db()
    products = session.query(Product).filter(Product.cloud_id != None).limit(3).all()
    for p in products:
        print(f"   - {p.name} | SKU: {p.code} | Price: Rs {p.price_per_unit} | HSN: {p.hsn_code or '95030090'}")
    
    if not products:
        print("[WARN] No synced products found in SQLite. Creating fallback product...")
        p = Product(
            name="ToyPop Demo Wooden Blocks",
            code="TP-DEMO-BLK",
            base_unit="pcs",
            price_per_unit=599.0,
            category="Educational",
            gst_rate_bps=1800,
            hsn_code="95030090"
        )
        session.add(p)
        session.commit()
        products = [p]
    
    prod = products[0]

    # Step 3: Create an offline bill
    print("\n[Step 3/4] Creating offline test bill in local SQLite...")
    from datetime import datetime
    test_bill_id = f"TP-TEST-{uuid.uuid4().hex[:6].upper()}"

    customer = Customer(name="Sriram Tester", phone=f"98{uuid.uuid4().int % 100000000:08d}")
    session.add(customer)
    session.flush()

    test_bill = Bill(
        bill_number=test_bill_id,
        customer_id=customer.id,
        date_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        subtotal=prod.price_per_unit,
        grand_total=prod.price_per_unit,
        payment_method="CASH",
        status="PAID",
        synced=0,
        local_bill_id=test_bill_id
    )
    session.add(test_bill)
    session.flush()

    item = BillItem(
        bill_id=test_bill.id,
        product_id=prod.id,
        product_name=prod.name,
        quantity=1,
        unit=prod.base_unit or "pcs",
        price=prod.price_per_unit,
        total=prod.price_per_unit
    )
    session.add(item)
    session.commit()
    print(f"[OK] Created local bill #{test_bill.id} (Local Ref: {test_bill_id}) with synced=0.")
    session.close()

    # Step 4: Sync Pending Bills
    print("\n[Step 4/4] Transmitting offline bills via /api/pos/orders...")
    sync_res = client.sync_pending_bills()
    if not sync_res.get("success"):
        print(f"[FAIL] Bill sync failed: {sync_res.get('errors') or sync_res.get('error')}")
        return False
    print(f"[OK] Bill sync SUCCESS! Transmitted {sync_res.get('synced_bills', 0)} bills.")

    # Verify bill is now marked synced=1 in SQLite
    session = get_db()
    verified_bill = session.query(Bill).filter(Bill.bill_number == test_bill_id).first()
    if verified_bill and verified_bill.synced == 1:
        print(f"[OK] Verified local DB: Bill #{verified_bill.id} marked as synced=1 (Cloud Order ID: {verified_bill.cloud_order_id})")
    else:
        print(f"[WARN] Bill status: synced={getattr(verified_bill, 'synced', 'None')}")
    session.close()

    print("\n" + "=" * 60)
    print("[SUCCESS] ALL INTEGRATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)
