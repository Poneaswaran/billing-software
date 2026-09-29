from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from app.db import Base
from datetime import datetime

class Product(Base):
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    code = Column(String)
    base_unit = Column(String, nullable=False)
    price_per_unit = Column(Float, nullable=False)
    category = Column(String)
    cloud_id = Column(String, index=True, nullable=True)
    stock_qty = Column(Integer, default=0)
    gst_rate_bps = Column(Integer, default=1800)
    hsn_code = Column(String, nullable=True)
    image_url = Column(String, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'base_unit': self.base_unit,
            'price_per_unit': self.price_per_unit,
            'category': self.category,
            'cloud_id': self.cloud_id,
            'stock_qty': self.stock_qty,
            'gst_rate_bps': self.gst_rate_bps,
            'hsn_code': self.hsn_code,
            'image_url': self.image_url
        }

class Customer(Base):
    __tablename__ = 'customers'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    phone = Column(String, unique=True)
    address = Column(String)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'phone': self.phone,
            'address': self.address
        }

class Bill(Base):
    __tablename__ = 'bills'
    
    id = Column(Integer, primary_key=True)
    bill_number = Column(String, unique=True, nullable=False)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=True)
    date_time = Column(String, nullable=False) # Keeping as string to match existing format
    subtotal = Column(Float, nullable=False)
    tax_percent = Column(Float, default=0)
    tax_amount = Column(Float, default=0)
    discount_amount = Column(Float, default=0)
    grand_total = Column(Float, nullable=False)
    payment_method = Column(String)
    status = Column(String, default='PAID')
    synced = Column(Integer, default=0, index=True)
    cloud_order_id = Column(String, nullable=True)
    local_bill_id = Column(String, nullable=True)
    
    customer = relationship("Customer")
    items = relationship("BillItem", back_populates="bill", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'bill_number': self.bill_number,
            'customer_id': self.customer_id,
            'date_time': self.date_time,
            'subtotal': self.subtotal,
            'tax_percent': self.tax_percent,
            'tax_amount': self.tax_amount,
            'discount_amount': self.discount_amount,
            'grand_total': self.grand_total,
            'payment_method': self.payment_method,
            'status': self.status,
            'synced': self.synced or 0,
            'cloud_order_id': self.cloud_order_id,
            'local_bill_id': self.local_bill_id,
            'customer_name': self.customer.name if self.customer else None,
            'customer_phone': self.customer.phone if self.customer else None
        }

class BillItem(Base):
    __tablename__ = 'bill_items'
    
    id = Column(Integer, primary_key=True)
    bill_id = Column(Integer, ForeignKey('bills.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    product_name = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    total = Column(Float, nullable=False)
    
    bill = relationship("Bill", back_populates="items")
    product = relationship("Product")

class Setting(Base):
    __tablename__ = 'settings'
    
    key = Column(String, primary_key=True)
    value = Column(String)
