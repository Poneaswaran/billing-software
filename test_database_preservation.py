"""Check installed-app data reuse without accessing the real local database."""
import builtins
from contextlib import closing
import hashlib
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

from app.db import get_db_path


class DatabasePreservationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.install = self.root / 'installed-app'
        self.install.mkdir()
        self.local = self.root / 'localappdata'
        self.bundle = self.install / '_internal'
        self.patches = [
            patch.object(sys, 'frozen', True, create=True),
            patch.object(sys, 'executable', str(self.install / 'ToyPopBilling.exe')),
            patch.object(sys, '_MEIPASS', str(self.bundle), create=True),
            patch.dict(os.environ, {'LOCALAPPDATA': str(self.local)}),
        ]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def make_database(self, directory, name):
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / 'thangam.db'
        with closing(sqlite3.connect(target)) as connection:
            connection.execute('CREATE TABLE bills (name TEXT)')
            connection.execute('INSERT INTO bills VALUES (?)', (name,))
            connection.commit()
        return target

    def test_upgrade_keeps_existing_database_instead_of_bundled_data(self):
        existing = self.make_database(self.install / 'data', 'Customer bill')
        self.make_database(self.bundle / 'data', 'Bundled sample')
        before = hashlib.sha256(existing.read_bytes()).hexdigest()
        self.assertEqual(Path(get_db_path()), existing)
        self.assertEqual(hashlib.sha256(existing.read_bytes()).hexdigest(), before)
        with closing(sqlite3.connect(existing)) as connection:
            self.assertEqual(connection.execute('SELECT name FROM bills').fetchone()[0], 'Customer bill')

    def test_read_only_install_reuses_existing_localappdata_database(self):
        existing = self.make_database(self.local / 'ToyPopBilling' / 'data', 'Saved offline bill')
        original_open = builtins.open

        def guarded_open(file, *args, **kwargs):
            if Path(file) == self.install / 'data' / '.perm_test':
                raise PermissionError('Read-only installation')
            return original_open(file, *args, **kwargs)

        before = existing.read_bytes()
        with patch('builtins.open', side_effect=guarded_open):
            self.assertEqual(Path(get_db_path()), existing)
        self.assertEqual(existing.read_bytes(), before)

    def test_fresh_install_without_bundled_database_does_not_copy_other_data(self):
        path = Path(get_db_path())
        self.assertEqual(path, self.install / 'data' / 'thangam.db')
        self.assertFalse(path.exists())  # init_db creates the new empty schema later.


if __name__ == '__main__':
    unittest.main()
