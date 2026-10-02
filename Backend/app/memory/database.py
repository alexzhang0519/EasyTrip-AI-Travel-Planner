"""SQLite connection lifetime for the existing local conversation database."""
import sqlite3
from contextlib import contextmanager
from flask import current_app

@contextmanager
def connection():
    root = current_app.config['STORAGE_DIR']
    root.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(root / 'conversations.sqlite3', timeout=15)
    try:
        with db:
            db.execute('CREATE TABLE IF NOT EXISTS conversations (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
            yield db
    finally:
        db.close()
