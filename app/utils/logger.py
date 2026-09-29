import logging
from logging.handlers import RotatingFileHandler
import os

import sys

def _get_log_dir():
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
        logs = os.path.join(base_dir, 'logs')
        try:
            os.makedirs(logs, exist_ok=True)
            test_file = os.path.join(logs, '.perm_test')
            with open(test_file, 'w') as f:
                f.write('1')
            os.remove(test_file)
            return logs
        except Exception:
            appdata = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
            fallback_logs = os.path.join(appdata, 'ToyPopBilling', 'logs')
            os.makedirs(fallback_logs, exist_ok=True)
            return fallback_logs
    else:
        dev_logs = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
        os.makedirs(dev_logs, exist_ok=True)
        return dev_logs

LOG_DIR = _get_log_dir()

def setup_logger(name, log_file, level=logging.INFO):
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler = RotatingFileHandler(os.path.join(LOG_DIR, log_file), maxBytes=10*1024*1024, backupCount=5)
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    return logger

# Create loggers
app_logger = setup_logger('app_logger', 'app.log')
error_logger = setup_logger('error_logger', 'error.log', level=logging.ERROR)
transaction_logger = setup_logger('transaction_logger', 'transaction.log')
