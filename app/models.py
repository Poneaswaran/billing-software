from app.db import get_db
from app.orm_models import Product, Customer, Bill, BillItem, Setting
from sqlalchemy import or_
from datetime import datetime

class ProductModel:
    @staticmethod
    def add_product(name, code, base_unit, price, category="General"):
        session = get_db()
        try:
            product = Product(name=name, code=code, base_unit=base_unit, price_per_unit=price, category=category)
            session.add(product)
            session.commit()
            return product.id
        finally:
            session.close()

    @staticmethod
    def get_all_products():
        session = get_db()
        try:
            products = session.query(Product).all()
            return [p.to_dict() for p in products]
        finally:
            session.close()

    @staticmethod
    def search_products(query):
        session = get_db()
        try:
            products = session.query(Product).filter(
                or_(Product.name.like(f'%{query}%'), Product.code.like(f'%{query}%'))
            ).all()
            return [p.to_dict() for p in products]
        finally:
            session.close()

    @staticmethod
    def update_product(product_id, name, code, base_unit, price, category):
        session = get_db()
        try:
            product = session.query(Product).get(product_id)
            if product:
                product.name = name
                product.code = code
                product.base_unit = base_unit
                product.price_per_unit = price
                product.category = category
                session.commit()
        finally:
            session.close()

    @staticmethod
    def delete_product(product_id):
        session = get_db()
        try:
            product = session.query(Product).get(product_id)
            if product:
                session.delete(product)
                session.commit()
        finally:
            session.close()

class CustomerModel:
    @staticmethod
    def add_customer(name, phone, address):
        session = get_db()
        try:
            customer = Customer(name=name, phone=phone, address=address)
            session.add(customer)
            session.commit()
            return customer.id
        except Exception:
            session.rollback()
            return None
        finally:
            session.close()

    @staticmethod
    def get_all_customers():
        session = get_db()
        try:
            customers = session.query(Customer).all()
            return [c.to_dict() for c in customers]
        finally:
            session.close()

    @staticmethod
    def search_customer(query):
        session = get_db()
        try:
            customers = session.query(Customer).filter(
                or_(Customer.name.like(f'%{query}%'), Customer.phone.like(f'%{query}%'))
            ).all()
            return [c.to_dict() for c in customers]
        finally:
            session.close()

    @staticmethod
    def update_customer(customer_id, name, phone, address):
        session = get_db()
        try:
            customer = session.query(Customer).get(customer_id)
            if customer:
                customer.name = name
                customer.phone = phone
                customer.address = address
                session.commit()
                return True
            return False
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()

    @staticmethod
    def delete_customer(customer_id):
        session = get_db()
        try:
            customer = session.query(Customer).get(customer_id)
            if customer:
                session.delete(customer)
                session.commit()
                return True
            return False
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()

class BillModel:
    @staticmethod
    def create_bill(bill_data, items):
        session = get_db()
        try:
            bill = Bill(
                bill_number=bill_data['bill_number'],
                customer_id=bill_data.get('customer_id'),
                date_time=bill_data['date_time'],
                subtotal=bill_data['subtotal'],
                tax_percent=bill_data.get('tax_percent', 0),
                tax_amount=bill_data.get('tax_amount', 0),
                discount_amount=bill_data.get('discount_amount', 0),
                grand_total=bill_data['grand_total'],
                payment_method=bill_data['payment_method']
            )
            session.add(bill)
            session.flush() # Get ID

            for item in items:
                bill_item = BillItem(
                    bill_id=bill.id,
                    product_id=item['product_id'],
                    product_name=item['product_name'],
                    quantity=item['quantity'],
                    unit=item['unit'],
                    price=item['price'],
                    total=item['total']
                )
                session.add(bill_item)
            
            session.commit()
            return bill.id
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    @staticmethod
    def get_recent_bills(limit=10):
        session = get_db()
        try:
            bills = session.query(Bill).order_by(Bill.id.desc()).limit(limit).all()
            return [b.to_dict() for b in bills]
        finally:
            session.close()

    @staticmethod
    def delete_all_bills():
        session = get_db()
        try:
            session.query(BillItem).delete()
            session.query(Bill).delete()
            session.commit()
        finally:
            session.close()

    @staticmethod
    def get_debt_bills():
        """Get all unpaid debt bills with customer info"""
        session = get_db()
        try:
            bills = session.query(Bill).filter(
                Bill.payment_method == 'Debt',
                Bill.status != 'PAID'
            ).order_by(Bill.id.desc()).all()
            return [b.to_dict() for b in bills]
        finally:
            session.close()

    @staticmethod
    def get_debt_by_customer():
        """Get total debt grouped by customer"""
        session = get_db()
        try:
            from sqlalchemy import func
            results = session.query(
                Customer.id,
                Customer.name,
                Customer.phone,
                func.sum(Bill.grand_total).label('total_debt'),
                func.count(Bill.id).label('bill_count')
            ).join(Customer, Bill.customer_id == Customer.id).filter(
                Bill.payment_method == 'Debt',
                Bill.status != 'PAID'
            ).group_by(Customer.id, Customer.name, Customer.phone).all()
            
            return [{
                'customer_id': r.id,
                'customer_name': r.name,
                'customer_phone': r.phone,
                'total_debt': r.total_debt,
                'bill_count': r.bill_count
            } for r in results]
        finally:
            session.close()

    @staticmethod
    def mark_bill_as_paid(bill_id):
        """Mark a debt bill as paid"""
        session = get_db()
        try:
            bill = session.query(Bill).get(bill_id)
            if bill:
                bill.status = 'PAID'
                session.commit()
                return True
            return False
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()

    @staticmethod
    def get_customer_debt_bills(customer_id):
        """Get all debt bills for a specific customer"""
        session = get_db()
        try:
            bills = session.query(Bill).filter(
                Bill.customer_id == customer_id,
                Bill.payment_method == 'Debt',
                Bill.status != 'PAID'
            ).order_by(Bill.id.desc()).all()
            return [b.to_dict() for b in bills]
        finally:
            session.close()

class SettingsModel:
    @staticmethod
    def get_setting(key, default=None):
        session = get_db()
        try:
            setting = session.query(Setting).filter_by(key=key).first()
            return setting.value if setting else default
        finally:
            session.close()

    @staticmethod
    def set_setting(key, value):
        session = get_db()
        try:
            setting = session.query(Setting).filter_by(key=key).first()
            if setting:
                setting.value = value
            else:
                setting = Setting(key=key, value=value)
                session.add(setting)
            session.commit()
        finally:
            session.close()
