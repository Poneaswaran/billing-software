from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os
import sys
import shutil

Base = declarative_base()

def get_db_path():
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        # Use a 'data' folder next to the executable for persistence if writable
        base_dir = os.path.dirname(sys.executable)
        data_dir = os.path.join(base_dir, 'data')
        
        try:
            os.makedirs(data_dir, exist_ok=True)
            test_file = os.path.join(data_dir, '.perm_test')
            with open(test_file, 'w') as f:
                f.write('1')
            os.remove(test_file)
        except Exception:
            # Fallback to LocalAppData if Program Files is read-only
            appdata = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
            data_dir = os.path.join(appdata, 'ToyPopBilling', 'data')
            os.makedirs(data_dir, exist_ok=True)
            
        db_path = os.path.join(data_dir, 'thangam.db')
        
        # If DB doesn't exist in persistent location, try to copy from bundled source
        if not os.path.exists(db_path):
            try:
                bundled_locations = [
                    os.path.join(getattr(sys, '_MEIPASS', ''), 'data', 'thangam.db'),
                    os.path.join(base_dir, '_internal', 'data', 'thangam.db'),
                    os.path.join(base_dir, 'data', 'thangam.db'),
                ]
                for bundled_db in bundled_locations:
                    if bundled_db and os.path.exists(bundled_db) and os.path.abspath(bundled_db) != os.path.abspath(db_path):
                        shutil.copy2(bundled_db, db_path)
                        break
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

