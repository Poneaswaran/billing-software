from datetime import datetime
import random
import string

def generate_bill_number():
    """Generates a unique bill number based on timestamp and random suffix."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
    return f"BILL-{timestamp}-{suffix}"

def convert_unit(value, from_unit, to_unit):
    """
    Converts units.
    Supported: g -> kg, ml -> litre
    """
    if from_unit == to_unit:
        return value
    
    if from_unit == 'g' and to_unit == 'kg':
        return value / 1000.0
    if from_unit == 'kg' and to_unit == 'g':
        return value * 1000.0
    
    if from_unit == 'ml' and to_unit == 'litre':
        return value / 1000.0
    if from_unit == 'litre' and to_unit == 'ml':
        return value * 1000.0
        
    return value

def format_currency(value):
    return f"₹{value:.2f}"
