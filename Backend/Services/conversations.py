"""Keep conversation content on disk, never in browser cookies."""
import json
import sqlite3
import uuid
from flask import current_app, session

def connection():
    root = current_app.config['STORAGE_DIR']
    root.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(root / 'conversations.sqlite3')
    db.execute('CREATE TABLE IF NOT EXISTS conversations (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
    return db

def read():
    if 'conversation_id' not in session:
        session['conversation_id'] = uuid.uuid4().hex
    with connection() as db:
        row = db.execute('SELECT data FROM conversations WHERE id = ?', (session['conversation_id'],)).fetchone()
    return json.loads(row[0]) if row else {'messages': [], 'pois': []}

def write(data):
    read()
    with connection() as db:
        db.execute('INSERT OR REPLACE INTO conversations VALUES (?, ?)',
                   (session['conversation_id'], json.dumps(data)))
