import threading
from pathlib import Path
from flask import request
from Backend.app.memory import trips as persistence

# This local app serializes planning, so simultaneous tabs cannot lose turns.
planning_lock = threading.Lock()

def payload():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValueError('Send a JSON object.')
    return data

def text_field(data, key, limit=2000):
    value = data.get(key)
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f'{key.capitalize()} must contain 1–{limit} characters.')
    return value.strip()

def trip_path(trip_id):
    if Path(trip_id).name != trip_id or not trip_id.endswith('.json'):
        raise ValueError('Invalid trip ID.')
    path = Path(persistence.TRIPS_DIR) / trip_id
    if not path.is_file() or path.is_symlink():
        raise FileNotFoundError()
    return str(path)

def visible(data):
    messages = persistence._clean_messages(data['messages'])
    # Legacy snapshots have only one POI list: attach it to the latest answer,
    # never to older answers that may discuss a different destination.
    last = next((m for m in reversed(messages) if m['role'] == 'assistant'), None)
    for m in messages:
        if m['role'] == 'assistant' and 'places' not in m:
            m['places'] = data['pois'] if m is last else []
    return {'messages': messages, 'pois': data['pois']}

