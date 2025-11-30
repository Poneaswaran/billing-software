from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import os
from datetime import datetime

Base = declarative_base()
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'thangam.db')
engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
Session = sessionmaker(bind=engine)

def get_db():
    return Session()

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    Base.metadata.create_all(engine)

# Define Models directly here to avoid circular imports if we were to separate them, 
# but typically they go in models.py. However, since models.py currently holds the *logic* 
# (DAO pattern), we will define the ORM classes here or in a new file. 
# To keep it clean, let's put the ORM class definitions in a new file `app/orm_models.py` 
# and keep `app/db.py` for connection setup.
