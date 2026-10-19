"""Isolated tests: no production database or network access."""
import unittest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db import Base
from app.models import ProductModel, BillModel
from app.orm_models import Product, Bill
from app.sync import ToyPopSyncClient


class ManualItemsTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)
        self.patches = [patch('app.models.get_db', self.session),
                        patch('app.sync.get_db', self.session),
                        patch('app.sync.ensure_db_columns'),
                        patch('app.sync.SettingsModel.get_setting', side_effect=lambda key, default='': default),
                        patch('app.sync.SettingsModel.set_setting')]
        for p in self.patches:
            p.start()
        self.client = ToyPopSyncClient(base_url='http://test', api_key='test', terminal_id='TEST')

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.engine.dispose()

    def test_name_only_item_is_persistent_and_reused(self):
        item = ProductModel.add_manual_product('  Wooden Train  ')
        self.assertEqual(item['name'], 'Wooden Train')
        self.assertEqual(item['price_per_unit'], 0)
        self.assertTrue(item['is_manual'])
        self.assertEqual(ProductModel.add_manual_product('wooden train')['id'], item['id'])

    def test_offline_upload_retries_same_id(self):
        item = ProductModel.add_manual_product('New Toy')
        with patch.object(self.client, '_make_request', return_value={'status': 0}) as request:
            self.assertFalse(self.client.sync_manual_items()['success'])
            self.assertEqual(request.call_args.kwargs['data']['localItemId'], item['cloud_id'])
        with patch.object(self.client, '_make_request', return_value={'status': 201}):
            self.assertTrue(self.client.sync_manual_items()['success'])
        with patch.object(self.client, '_make_request') as request:
            self.client.sync_manual_items()
            request.assert_not_called()

    def test_full_catalog_refresh_preserves_manual_item(self):
        item = ProductModel.add_manual_product('Custom Toy')
        with patch.object(self.client, '_make_request', return_value={'status': 200, 'data': {
            'mode': 'full', 'generation': 2, 'syncToken': '1', 'items': [], 'hasMore': False
        }}):
            self.assertTrue(self.client.sync_catalog()['success'])
        with self.session() as session:
            self.assertEqual(session.get(Product, item['id']).name, 'Custom Toy')

    def test_pos_status_product_without_image_is_downloaded_for_billing(self):
        with patch.object(self.client, '_make_request', return_value={'status': 200, 'data': {
            'mode': 'full', 'generation': 2, 'syncToken': '1', 'hasMore': False,
            'items': [{'id': 'pos-only', 'name': 'Counter Toy', 'sku': 'COUNTER-1',
                       'status': 'pos', 'pricePaise': 2500, 'stock': 5, 'imageUrl': ''}]
        }}):
            self.assertTrue(self.client.sync_catalog()['success'])
        downloaded = ProductModel.get_all_products()
        self.assertEqual(len(downloaded), 1)
        self.assertEqual(downloaded[0]['name'], 'Counter Toy')
        self.assertEqual(downloaded[0]['price_per_unit'], 25)
        self.assertFalse(downloaded[0]['image_url'])

    def test_bill_payload_preserves_manual_name_and_discount(self):
        item = ProductModel.add_manual_product('Typed Item')
        BillModel.create_bill({
            'bill_number': 'TEST-1', 'date_time': '2026-10-19 12:00:00',
            'subtotal': 100, 'discount_amount': 10, 'grand_total': 90, 'payment_method': 'Cash'
        }, [{'product_id': item['id'], 'product_name': item['name'], 'quantity': 1,
             'unit': 'pc', 'price': 100, 'total': 100}])
        with patch.object(self.client, '_make_request', return_value={
            'status': 201, 'data': {'success': True, 'orderId': 'cloud-order'}
        }) as request:
            self.assertTrue(self.client.sync_pending_bills()['success'])
            payload = request.call_args.kwargs['data']
            self.assertEqual(payload['discountPaise'], 1000)
            self.assertEqual(payload['totalPaise'], 9000)
            self.assertEqual(payload['items'][0]['name'], 'Typed Item')
            self.assertTrue(payload['items'][0]['isManual'])
        with self.session() as session:
            self.assertEqual(session.query(Bill).one().synced, 1)

    def test_add_item_uses_typed_name_without_dialog(self):
        from app.ui_main import MainWindow
        window = MagicMock()
        window.products = []
        window.prod_search.text.return_value = 'Unlisted Toy'
        with patch('app.ui_main.SettingsModel.get_setting', return_value=''), \
             patch('app.ui_main.show_error') as error:
            MainWindow.add_product_to_cart_manual(window)
        error.assert_not_called()
        self.assertEqual(window.add_to_cart.call_args.args[0]['name'], 'Unlisted Toy')
        self.assertEqual(window.add_to_cart.call_args.args[0]['price_per_unit'], 0)
        window.queue_manual_item_sync.assert_called_once()


if __name__ == '__main__':
    unittest.main()
