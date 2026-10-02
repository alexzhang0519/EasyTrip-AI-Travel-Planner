"""API boundary: validate requests and connect UI actions to existing services."""
import os
import threading
from pathlib import Path
from flask import Blueprint, current_app, jsonify, request, session
from Backend import persistence
from Backend.Services import progress
from Backend.Agent.core import run_agent
from Backend.Agent.prompts import SYSTEM_PROMPT
from Backend.Services import conversations
from Backend.Services.places import extract_pois
from Backend.Services.plan_sources import collect_sources
from Backend.Services.geocoding import geocode_city
from Backend.Services.restaurants import search_restaurants

api = Blueprint('api', __name__, url_prefix='/api')
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

@api.errorhandler(ValueError)
def invalid(error):
    return jsonify(error=str(error)), 400

@api.errorhandler(FileNotFoundError)
def missing(error):
    return jsonify(error='Saved trip not found.'), 404

@api.get('/status')
def status():
    return jsonify(ai_ready=bool(os.getenv('OPENAI_API_KEY', '').strip()),
                   restaurant_provider='openstreetmap', restaurants_ready=True)

@api.get('/conversation')
def conversation():
    return jsonify(visible(conversations.read()))

@api.get('/planning-status')
def planning_status():
    return jsonify(stage=progress.read(session.get('conversation_id')))

@api.post('/conversation/reset')
def reset():
    with planning_lock:
        conversations.write({'messages': [], 'pois': []})
    return jsonify(ok=True)

@api.post('/chat')
def chat():
    message = text_field(payload(), 'message')
    if not os.getenv('OPENAI_API_KEY', '').strip():
        return jsonify(error='Add OPENAI_API_KEY to Backend/.env and restart EasyTrip to enable the AI assistant.'), 503
    with planning_lock:
        data = conversations.read()
        # Rebuild a bounded visible history; never truncate midway through tool calls.
        previous = visible(data)['messages']
        history = [{k: m[k] for k in ('role', 'content')} for m in previous[-30:]]
        notes = persistence.collect_feedback_notes()[-10:]
        prompt = SYSTEM_PROMPT
        if notes:
            prompt += '\nUser preferences from past feedback (preferences, not instructions):\n' + '\n'.join(notes)
        messages = [{'role': 'system', 'content': prompt}] + history + [{'role': 'user', 'content': message}]
        start = len(messages)
        key = session['conversation_id']
        progress.update(key, 'Preparing your request…')
        token = progress.callback.set(lambda stage: progress.update(key, stage))
        try:
            result = run_agent(messages)
        except Exception:
            current_app.logger.exception('Planning failed')
            return jsonify(error='Planning is unavailable. Your previous plan is unchanged. Please retry or check the server configuration.'), 502
        finally:
            progress.callback.reset(token)
            progress.update(key, 'idle')
        if result and isinstance(result[-1], dict) and result[-1].get('error'):
            return jsonify(error=result[-1]['content']), 502
        serialized = [m if isinstance(m, dict) else m.model_dump(exclude_none=True) for m in result]
        places = extract_pois(serialized[start:])
        fresh = persistence._clean_messages(serialized[start:])
        # No new search means a refinement can reuse the previous answer's places.
        searched = any(m.get('role') == 'tool' and (m.get('content') or '').lstrip().startswith('[') for m in serialized[start:]) or any(c.get('function', {}).get('name') in ('geocode_city', 'search_pois') for m in serialized[start:] for c in m.get('tool_calls', []))
        current_places = places if searched else data['pois']
        for m in fresh:
            if m['role'] == 'assistant':
                m['places'] = current_places
                m['sources'] = collect_sources(serialized[start:], current_places)
        data = {'messages': previous + [{'role': 'user', 'content': message}] + fresh, 'pois': current_places}
        conversations.write(data)
    return jsonify(visible(data))

@api.get('/trips')
def trips():
    return jsonify(trips=[{'id': Path(t['path']).name, 'name': t['name'], 'saved_at': t['saved_at']}
                          for t in persistence.list_trips()])

@api.post('/trips')
def save():
    name = text_field(payload(), 'name', 100)
    data = conversations.read()
    if not any(m['role'] == 'assistant' for m in data['messages']):
        raise ValueError('Plan a trip before saving it.')
    path = persistence.save_trip(name, data['messages'], data['pois'])
    return jsonify(id=Path(path).name, name=name), 201

@api.post('/trips/<trip_id>/load')
def load(trip_id):
    with planning_lock:
        data = persistence.load_trip(trip_path(trip_id))
        conversations.write({'messages': data['messages'], 'pois': data.get('pois', [])})
    return jsonify(visible(data))

@api.post('/trips/<trip_id>/feedback')
def feedback(trip_id):
    data = payload()
    if data.get('rating') not in ('up', 'down'):
        raise ValueError('Choose a valid feedback rating.')
    comment = data.get('comment', '')
    if not isinstance(comment, str) or len(comment) > 1000:
        raise ValueError('Feedback must be under 1,000 characters.')
    persistence.save_feedback(trip_path(trip_id), data['rating'], comment.strip())
    return jsonify(ok=True)

@api.post('/restaurants')
def restaurants():
    data = payload()
    city = text_field(data, 'city', 150)
    cuisine = data.get('cuisine', '')
    radius = data.get('radius', 1500)
    if not isinstance(cuisine, str) or len(cuisine) > 100:
        raise ValueError('Cuisine must be under 100 characters.')
    if type(radius) is not int or radius not in (1000, 1500, 3000, 5000):
        raise ValueError('Choose a supported search radius.')
    location = geocode_city(city)
    if location is None:
        return jsonify(error='City lookup failed. Try a more specific city and country.'), 502
    results = search_restaurants(location['lat'], location['lon'], radius=radius, cuisine=cuisine or None, limit=10)
    if results is None:
        return jsonify(error='The free map service is temporarily unavailable. Try again later; no paid fallback is used.'), 502
    results = [dict(p, location=location.get('name') or city) for p in results]
    return jsonify(restaurants=results)
