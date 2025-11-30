from app.db import get_db_connection
from datetime import datetime
import json

class ProductModel:
    @staticmethod
    def add_product(name, code, base_unit, price, category="General"):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO products (name, code, base_unit, price_per_unit, category) VALUES (?, ?, ?, ?, ?)',
                           (name, code, base_unit, price, category))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    @staticmethod
    def get_all_products():
        conn = get_db_connection()
        products = conn.execute('SELECT * FROM products').fetchall()
        conn.close()
        return [dict(p) for p in products]

    @staticmethod
    def search_products(query):
        conn = get_db_connection()
        products = conn.execute('SELECT * FROM products WHERE name LIKE ? OR code LIKE ?', 
                                (f'%{query}%', f'%{query}%')).fetchall()
        conn.close()
        return [dict(p) for p in products]

    @staticmethod
    def update_product(product_id, name, code, base_unit, price, category):
        conn = get_db_connection()
        conn.execute('UPDATE products SET name=?, code=?, base_unit=?, price_per_unit=?, category=? WHERE id=?',
                     (name, code, base_unit, price, category, product_id))
        conn.commit()
        conn.close()

    @staticmethod
    def delete_product(product_id):
        conn = get_db_connection()
        conn.execute('DELETE FROM products WHERE id=?', (product_id,))
        conn.commit()
        conn.close()

class CustomerModel:
    @staticmethod
    def add_customer(name, phone, address):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO customers (name, phone, address) VALUES (?, ?, ?)',
                           (name, phone, address))
            conn.commit()
            return cursor.lastrowid
        except Exception:
            return None # Likely duplicate phone
        finally:
            conn.close()

    @staticmethod
    def get_all_customers():
        conn = get_db_connection()
        customers = conn.execute('SELECT * FROM customers').fetchall()
        conn.close()
        return [dict(c) for c in customers]

    @staticmethod
    def search_customer(query):
        conn = get_db_connection()
        customers = conn.execute('SELECT * FROM customers WHERE name LIKE ? OR phone LIKE ?',
                                 (f'%{query}%', f'%{query}%')).fetchall()
        conn.close()
        return [dict(c) for c in customers]

class BillModel:
    @staticmethod
    def create_bill(bill_data, items):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO bills (bill_number, customer_id, date_time, subtotal, tax_percent, tax_amount, discount_amount, grand_total, payment_method)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                bill_data['bill_number'],
                bill_data.get('customer_id'),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                bill_data['subtotal'],
                bill_data.get('tax_percent', 0),
                bill_data.get('tax_amount', 0),
                bill_data.get('discount_amount', 0),
                bill_data['grand_total'],
                bill_data['payment_method']
            ))
            bill_id = cursor.lastrowid

            for item in items:
                cursor.execute('''
                    INSERT INTO bill_items (bill_id, product_id, product_name, quantity, unit, price, total)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    bill_id,
                    item['product_id'],
                    item['product_name'],
                    item['quantity'],
                    item['unit'],
                    item['price'],
                    item['total']
                ))
            
            conn.commit()
            return bill_id
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def get_recent_bills(limit=10):
        conn = get_db_connection()
        bills = conn.execute('SELECT * FROM bills ORDER BY id DESC LIMIT ?', (limit,)).fetchall()
        conn.close()
        return [dict(b) for b in bills]

class SettingsModel:
    @staticmethod
    def get_setting(key, default=None):
        conn = get_db_connection()
        row = conn.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
        conn.close()
        return row['value'] if row else default

    @staticmethod
    def set_setting(key, value):
        conn = get_db_connection()
        conn.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
        conn.commit()
        conn.close()
