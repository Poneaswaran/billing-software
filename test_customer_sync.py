"""Customer sync tests with isolated SQLite and mocked transport."""
from unittest.mock import patch
import unittest
import test_manual_items
from app.models import CustomerModel, BillModel
from app.orm_models import Customer
from sqlalchemy import text
from app.sync import ensure_db_columns


class CustomerSyncTests(unittest.TestCase):
    setUp = test_manual_items.ManualItemsTests.setUp
    tearDown = test_manual_items.ManualItemsTests.tearDown

    def test_legacy_customer_migration_preserves_details_and_identity(self):
        with self.engine.begin() as connection:
            connection.execute(text('DROP TABLE customers'))
            connection.execute(text('CREATE TABLE customers (id INTEGER PRIMARY KEY, name VARCHAR, phone VARCHAR, address VARCHAR)'))
            connection.execute(text("INSERT INTO customers VALUES (1, 'Existing', '9876543210', 'Original address')"))
        with patch('app.sync.init_db'):
            ensure_db_columns()
            with self.engine.connect() as connection:
                first = dict(connection.execute(text('SELECT * FROM customers')).mappings().one())
            ensure_db_columns()
            with self.engine.connect() as connection:
                second = dict(connection.execute(text('SELECT * FROM customers')).mappings().one())
        self.assertEqual(first, second)
        self.assertEqual(first['name'], 'Existing')
        self.assertEqual(first['address'], 'Original address')
        self.assertRegex(first['sync_id'], r'^pos_customer_[a-f0-9]{32}$')
        self.assertEqual(first['synced_version'], 0)
    def test_customer_retries_without_a_bill_and_keeps_identity(self):
        customer = CustomerModel.add_customer(' Test Customer ', '9876543210', 'Shop Road')
        with patch.object(self.client, '_make_request', return_value={'status': 0}) as request:
            self.assertFalse(self.client.sync_pending_customers()['success'])
            identity = request.call_args.kwargs['data']['localCustomerId']
        with patch.object(self.client, '_make_request', return_value={
            'status': 201, 'data': {'success': True, 'customerId': 'website-customer'}
        }) as request:
            self.assertTrue(self.client.sync_pending_customers()['success'])
            self.assertEqual(request.call_args.kwargs['data']['localCustomerId'], identity)
            self.assertEqual(request.call_args.kwargs['data']['name'], 'Test Customer')
        with self.session() as session:
            saved = session.get(Customer, customer)
            self.assertEqual(saved.cloud_id, 'website-customer')
            self.assertEqual(saved.synced_version, saved.sync_version)
        with patch.object(self.client, '_make_request') as request:
            self.client.sync_pending_customers()
            request.assert_not_called()

    def test_edit_during_upload_remains_pending(self):
        customer = CustomerModel.add_customer('Original', '9876543210', '')
        def upload(*args, **kwargs):
            CustomerModel.update_customer(customer, 'Edited', '9876543210', 'New address')
            return {'status': 201, 'data': {'success': True, 'customerId': 'website-customer'}}
        with patch.object(self.client, '_make_request', side_effect=upload):
            self.client.sync_pending_customers()
        with self.session() as session:
            saved = session.get(Customer, customer)
            self.assertEqual(saved.sync_version, 2)
            self.assertEqual(saved.synced_version, 1)
        with patch.object(self.client, '_make_request', return_value={
            'status': 200, 'data': {'success': True, 'customerId': 'website-customer'}
        }) as request:
            self.client.sync_pending_customers()
            self.assertEqual(request.call_args.kwargs['data']['version'], 2)
            self.assertEqual(request.call_args.kwargs['data']['name'], 'Edited')

    def test_bill_waits_for_customer_then_sends_stable_link(self):
        customer = CustomerModel.add_customer('Bill Customer', '9876543210', '')
        BillModel.create_bill({
            'bill_number': 'CUSTOMER-1', 'customer_id': customer,
            'date_time': '2026-10-19 12:00:00', 'subtotal': 0,
            'discount_amount': 0, 'grand_total': 0, 'payment_method': 'Cash',
        }, [])
        with patch.object(self.client, '_make_request', return_value={'status': 0}) as request:
            self.assertFalse(self.client.sync_pending_bills()['success'])
            self.assertTrue(all(call.args[0] == '/api/pos/customers' for call in request.call_args_list))
        def upload(path, **kwargs):
            if path == '/api/pos/customers':
                return {'status': 201, 'data': {'success': True, 'customerId': 'website-customer'}}
            self.assertEqual(path, '/api/pos/orders')
            self.assertRegex(kwargs['data']['customer']['localCustomerId'], r'^pos_customer_[a-f0-9]{32}$')
            return {'status': 201, 'data': {'success': True, 'orderId': 'website-order'}}
        with patch.object(self.client, '_make_request', side_effect=upload):
            self.assertTrue(self.client.sync_pending_bills()['success'])
