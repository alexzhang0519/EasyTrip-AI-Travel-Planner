"""Tab-scoped browser drafts; SQLite compatibility for older API clients."""
import json
import uuid
from flask import current_app, session, request
import re

from .database import connection

def browser_key():
    token = request.headers.get('X-EasyTrip-Draft')
    if token is None:
        return None  # Compatibility for existing non-browser API clients.
    if not re.fullmatch(r'[a-f0-9-]{36}', token):
        raise ValueError('Invalid draft identifier.')
    if 'conversation_id' not in session:
        session['conversation_id'] = uuid.uuid4().hex
    return session['conversation_id'] + ':' + token

def store():
    return current_app.extensions['draft_store']

def progress_key():
    return browser_key() or session.get('conversation_id')

def start():
    key = browser_key()
    if key:
        # Retire the old cookie-shared disk draft when upgrading this browser.
        with connection() as db:
            db.execute('DELETE FROM conversations WHERE id = ?', (session['conversation_id'],))
        return store().start(key)
    return read()

def close():
    key = browser_key()
    if key:
        store().close(key)
    else:
        clear()

def read():
    key = browser_key()
    if key:
        return store().read(key)
    if 'conversation_id' not in session:
        session['conversation_id'] = uuid.uuid4().hex
    with connection() as db:
        row = db.execute('SELECT data FROM conversations WHERE id = ?', (session['conversation_id'],)).fetchone()
    return json.loads(row[0]) if row else {'messages': [], 'pois': []}

def write(data):
    key = browser_key()
    if key:
        store().write(key, data)
        return
    read()
    with connection() as db:
        db.execute('INSERT OR REPLACE INTO conversations VALUES (?, ?)',
                   (session['conversation_id'], json.dumps(data)))


def clear():
    """Clear only the current draft; saved trip snapshots are separate."""
    key = browser_key()
    if key:
        store().write(key, {'messages': [], 'pois': []})
        return
    conversation_id = session.get('conversation_id')
    if conversation_id:
        with connection() as db:
            db.execute('DELETE FROM conversations WHERE id = ?', (conversation_id,))
