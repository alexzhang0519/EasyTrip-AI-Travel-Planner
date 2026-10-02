import json
import pytest
from Backend.app import create_app
from Backend.app.memory import trips as persistence
from Backend.app.api.routes import chat as routes, map as map_routes

HEADERS = {'X-EasyTrip': '1'}

@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, 'TRIPS_DIR', str(tmp_path / 'itineraries'))
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.delenv('YELP_API_KEY', raising=False)
    return create_app({'TESTING': True, 'SECRET_KEY': 'test-secret', 'STORAGE_DIR': tmp_path})

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.mark.parametrize('path', ['/', '/planner', '/trips', '/restaurants', '/static/css/style.css', '/static/js/planner.js'])
def test_pages_and_assets(client, path):
    assert client.get(path).status_code == 200

def test_missing_configuration_and_validation(client):
    assert client.get('/api/status').json == {'ai_ready': False, 'restaurant_provider': 'openstreetmap', 'restaurants_ready': True}
    assert client.post('/api/chat', json={'message': 'Kyoto'}, headers=HEADERS).status_code == 503
    assert client.post('/api/chat', json={'message': []}, headers=HEADERS).status_code == 400
    assert client.post('/api/chat', json=[], headers=HEADERS).status_code == 400
    assert client.post('/api/trips', json={'name': 'Empty'}, headers=HEADERS).status_code == 400

def test_write_protection(client):
    assert client.post('/api/conversation/reset', json={}).status_code == 403
    assert client.post('/api/conversation/reset', json={}, headers={**HEADERS, 'Origin': 'https://other.example'}).status_code == 403

def test_chat_save_load_feedback_and_isolation(client, app, monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
    calls = []
    def fake_agent(messages):
        calls.append(messages.copy())
        messages.extend([{'role': 'tool', 'content': json.dumps([{'name': 'Garden', 'lat': 35, 'lon': 135, 'kind': 'sight'}])},
                         {'role': 'assistant', 'content': 'Visit Garden.'}])
        return messages
    monkeypatch.setattr(routes, 'run_agent', fake_agent)
    reply = client.post('/api/chat', json={'message': 'Kyoto'}, headers=HEADERS)
    assert reply.status_code == 200
    assert reply.json['pois'][0]['name'] == 'Garden'
    assert all(m['role'] in ('user', 'assistant') for m in reply.json['messages'])
    client.post('/api/chat', json={'message': 'Make it slower'}, headers=HEADERS)
    assert any(m['content'] == 'Kyoto' for m in calls[-1])
    assert app.test_client().get('/api/conversation').json['messages'] == []
    saved = client.post('/api/trips', json={'name': 'Kyoto'}, headers=HEADERS)
    assert saved.status_code == 201
    trip_id = saved.json['id']
    assert client.get('/api/trips').json['trips'][0]['id'] == trip_id
    assert 'path' not in client.get('/api/trips').json['trips'][0]
    client.post('/api/conversation/reset', json={}, headers=HEADERS)
    assert client.get('/api/conversation').json['messages'] == []
    loaded = client.post(f'/api/trips/{trip_id}/load', json={}, headers=HEADERS)
    assert loaded.json['messages'][-1]['content'] == 'Visit Garden.'
    assert client.post(f'/api/trips/{trip_id}/feedback', json={'rating': 'down', 'comment': 'Less walking'}, headers=HEADERS).status_code == 200
    client.post('/api/chat', json={'message': 'Another trip'}, headers=HEADERS)
    assert 'Less walking' in calls[-1][0]['content']
    assert client.post('/api/trips/missing.json/load', json={}, headers=HEADERS).status_code == 404
    assert client.post('/api/trips/secret.env/load', json={}, headers=HEADERS).status_code == 400

def test_restaurants_do_not_enter_conversation(client, monkeypatch):
    monkeypatch.setattr(map_routes, 'geocode_city', lambda city: {'lat': 35, 'lon': 135})
    monkeypatch.setattr(map_routes, 'search_restaurants', lambda *args, **kwargs: [{'name': 'Cafe', 'source': 'openstreetmap'}])
    assert client.post('/api/restaurants', json={'city': 'Kyoto'}, headers=HEADERS).json['restaurants'][0]['name'] == 'Cafe'
    assert client.get('/api/conversation').json == {'messages': [], 'pois': []}

def test_agent_failure_preserves_previous_conversation(client, monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
    def fail(messages):
        raise RuntimeError('service failure')
    monkeypatch.setattr(routes, 'run_agent', fail)
    assert client.post('/api/chat', json={'message': 'Kyoto'}, headers=HEADERS).status_code == 502
    assert client.get('/api/conversation').json['messages'] == []
