import unittest
from unittest.mock import patch
import test_manual_items
from app.models import BillModel, ProductModel
from app.orm_models import Bill
from app.sync import ensure_db_columns

class HeldAndDiscountTests(unittest.TestCase):
    setUp = test_manual_items.ManualItemsTests.setUp
    tearDown = test_manual_items.ManualItemsTests.tearDown

    def test_bill_edits_increment_revision_keep_identity_and_sync_latest_values(self):
        data = {'bill_number': 'EDIT-1', 'date_time': '2026-11-16 12:00:00',
                'subtotal': 100, 'discount_amount': 0, 'grand_total': 100, 'payment_method': 'Cash'}
        bill_id = BillModel.create_bill(data, [])
        response = {'status': 200, 'data': {'success': True, 'orderId': 'website-order'}}
        with patch.object(self.client, '_make_request', return_value=response) as request:
            self.client.sync_pending_bills()
            original = request.call_args.kwargs['data']
        self.assertEqual(original['revision'], 1)
        edited = dict(data, grand_total=90, discount_amount=10, date_time='2026-11-17 12:00:00')
        BillModel.update_bill(bill_id, edited, [])
        with patch.object(self.client, '_make_request', return_value=response) as request:
            self.client.sync_pending_bills()
            payload = request.call_args.kwargs['data']
        self.assertEqual(payload['revision'], 2)
        self.assertEqual(payload['localBillId'], original['localBillId'])
        self.assertEqual(payload['billedAt'], original['billedAt'])
        self.assertEqual(payload['totalPaise'], 9000)
        with self.session() as session:
            self.assertEqual(session.get(Bill, bill_id).synced, 1)

    def test_edit_while_uploading_remains_pending_until_its_own_revision_uploads(self):
        data = {'bill_number': 'EDIT-RACE', 'date_time': '2026-11-16 12:00:00',
                'subtotal': 100, 'grand_total': 100, 'payment_method': 'Cash'}
        bill_id = BillModel.create_bill(data, [])
        def upload(*args, **kwargs):
            self.assertEqual(kwargs['data']['revision'], 1)
            BillModel.update_bill(bill_id, dict(data, grand_total=80, discount_amount=20), [])
            return {'status': 201, 'data': {'success': True, 'orderId': 'website-order'}}
        with patch.object(self.client, '_make_request', side_effect=upload):
            self.client.sync_pending_bills()
        with self.session() as session:
            saved = session.get(Bill, bill_id)
            self.assertEqual(saved.sync_version, 2)
            self.assertEqual(saved.synced, 0)
        with patch.object(self.client, '_make_request', return_value={
            'status': 200, 'data': {'success': True, 'orderId': 'website-order'}
        }) as request:
            self.client.sync_pending_bills()
            self.assertEqual(request.call_args.kwargs['data']['revision'], 2)
            self.assertEqual(request.call_args.kwargs['data']['totalPaise'], 8000)

    def test_legacy_bill_revision_migration_preserves_records(self):
        from sqlalchemy import text
        with self.engine.begin() as connection:
            connection.execute(text('ALTER TABLE bills DROP COLUMN sync_version'))
            connection.execute(text("INSERT INTO bills (bill_number, date_time, subtotal, grand_total, synced, cloud_order_id) VALUES ('LEGACY', '2026-11-16 12:00:00', 100, 90, 0, 'cloud')"))
        with patch('app.sync.init_db'):
            ensure_db_columns()
            ensure_db_columns()
        with self.engine.connect() as connection:
            row = connection.execute(text('SELECT sync_version, grand_total FROM bills')).one()
        self.assertEqual(tuple(row), (2, 90))

    def test_legacy_item_discount_migration_is_repeatable(self):
        from sqlalchemy import text
        with self.engine.begin() as connection:
            connection.execute(text('ALTER TABLE bill_items DROP COLUMN discount_amount'))
        with patch('app.sync.init_db'):
            ensure_db_columns()
            ensure_db_columns()
        with self.engine.connect() as connection:
            columns = [row[1] for row in connection.execute(text('PRAGMA table_info(bill_items)'))]
        self.assertEqual(columns.count('discount_amount'), 1)

    def test_held_bill_never_uploads_then_completed_bill_keeps_line_discount(self):
        product = ProductModel.add_manual_product('Discount Toy')
        items = [{'product_id': product['id'], 'product_name': 'Discount Toy',
                  'quantity': 2, 'unit': 'pc', 'price': 100, 'discount_amount': 25, 'total': 175}]
        data = {'bill_number': 'HOLD-1', 'date_time': '2026-11-16 12:00:00',
                'subtotal': 200, 'discount_amount': 35, 'grand_total': 165, 'payment_method': 'Cash'}
        held = BillModel.hold_bill(data, items)
        with patch.object(self.client, 'sync_manual_items'), patch.object(self.client, '_make_request') as request:
            self.client.sync_pending_bills()
            request.assert_not_called()
        restored = BillModel.get_bill_items(held)
        self.assertEqual(restored[0]['discount_amount'], 25)
        BillModel.delete_bill(held)
        data['bill_number'] = 'PAID-1'
        paid = BillModel.create_bill(data, restored)
        with patch.object(self.client, 'sync_manual_items'), patch.object(self.client, '_make_request', return_value={
            'status': 201, 'data': {'success': True, 'orderId': 'cloud-order'}
        }) as request:
            result = self.client.sync_pending_bills()
            self.assertTrue(result['success'])
            payload = request.call_args.kwargs['data']
            self.assertEqual(payload['items'][0]['discountPaise'], 2500)
            self.assertEqual(payload['discountPaise'], 3500)
            self.assertEqual(payload['totalPaise'], 16500)
        with self.session() as session:
            self.assertEqual(session.get(Bill, paid).synced, 1)
        BillModel.update_bill(paid, data, restored)
        self.assertEqual(BillModel.get_bill_items(paid)[0]['discount_amount'], 25)

if __name__ == '__main__':
    unittest.main()
