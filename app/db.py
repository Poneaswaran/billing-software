from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os
import sys
import shutil

Base = declarative_base()

def get_db_path():
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        # Use a 'data' folder next to the executable for persistence
        base_dir = os.path.dirname(sys.executable)
        data_dir = os.path.join(base_dir, 'data')
        db_path = os.path.join(data_dir, 'thangam.db')
        
        # Create persistent data directory if it doesn't exist
        os.makedirs(data_dir, exist_ok=True)
        
        # If DB doesn't exist in persistent location, try to copy from bundled source
        if not os.path.exists(db_path):
            try:
                # sys._MEIPASS is where PyInstaller unpacks bundled files
                bundled_db = os.path.join(sys._MEIPASS, 'data', 'thangam.db')
                if os.path.exists(bundled_db):
                    shutil.copy2(bundled_db, db_path)
            except Exception as e:
                print(f"Error copying bundled DB: {e}")
                pass
                
        return db_path
    else:
        # Running from source
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'thangam.db')

DB_PATH = get_db_path()
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
Session = sessionmaker(bind=engine)

def get_db():
    return Session()

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    import app.orm_models
    Base.metadata.create_all(engine)

