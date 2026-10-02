import uuid
from pathlib import Path
from Backend.app.api.routes import chat as routes
from Backend.app.memory import conversations, trips
from Backend.app.memory.drafts import DraftStore
from test_app import app, client, HEADERS
import pytest


def tab():
    return {**HEADERS, 'X-EasyTrip-Draft': str(uuid.uuid4())}


def mock_planner(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'test-only')
    monkeypatch.setattr(routes, 'run_agent', lambda messages: messages + [
        {'role': 'assistant', 'content': 'Day 1: Garden and lunch.'}])


def test_second_tab_cannot_erase_first_tabs_plan_or_prevent_save(client, app, monkeypatch):
    mock_planner(monkeypatch)
    first, second = tab(), tab()
    assert client.post('/api/conversation/start', json={}, headers=first).status_code == 200
    plan = client.post('/api/chat', json={'message':'Kyoto'}, headers=first)
    assert plan.status_code == 200
    assert client.post('/api/conversation/start', json={}, headers=second).json == {'messages':[], 'pois':[]}
    client.post('/api/conversation/reset', json={}, headers=second)
    saved = client.post('/api/trips', json={'name':'My trip'}, headers=first)
    assert saved.status_code == 201
    assert client.get('/api/conversation', headers=first).json == plan.json
    assert client.post('/api/trips', json={'name':'Empty tab'}, headers=second).status_code == 400
    assert client.post('/api/conversation/close', json={}, headers=first).status_code == 200
    assert client.get('/api/conversation', headers=first).status_code == 400
    # No browser draft content is written to SQLite.
    with app.app_context(), conversations.connection() as db:
        assert db.execute('SELECT COUNT(*) FROM conversations').fetchone()[0] == 0
    reloaded = client.post('/api/trips/'+saved.json['id']+'/load', json={}, headers=second)
    assert reloaded.json == plan.json
    client.post('/api/conversation/close', json={}, headers=second)
    assert (Path(trips.TRIPS_DIR) / saved.json['id']).is_file()
    assert client.post('/api/trips/'+saved.json['id']+'/delete', json={}, headers=HEADERS).status_code == 200


def test_close_during_generation_rejects_late_result(client, monkeypatch):
    mock_planner(monkeypatch)
    first = tab()
    client.post('/api/conversation/start', json={}, headers=first)
    def late_result(messages):
        conversations.close()
        return messages + [{'role':'assistant','content':'Late plan'}]
    monkeypatch.setattr(routes, 'run_agent', late_result)
    result = client.post('/api/chat', json={'message':'Kyoto'}, headers=first)
    assert result.status_code == 400
    assert client.post('/api/conversation/start', json={}, headers=first).status_code == 400
    assert client.get('/api/conversation', headers=first).status_code == 400


def test_expiration_removes_abandoned_content(monkeypatch):
    from Backend.app.memory import drafts
    now = [100.0]
    monkeypatch.setattr(drafts, 'monotonic', lambda: now[0])
    store = DraftStore(ttl=10)
    monkeypatch.setattr(store, '_schedule', lambda: None)
    store.start('tab')
    store.write('tab', {'messages':[{'role':'user','content':'private draft'}], 'pois':[]})
    now[0] = 111
    store._tick()
    assert store.entries == {}
    with pytest.raises(ValueError, match='expired'):
        store.read('tab')


def test_browser_draft_requires_its_own_cookie_and_valid_id(client, app):
    first = tab()
    assert client.post('/api/conversation/start', json={}, headers=first).status_code == 200
    assert app.test_client().get('/api/conversation', headers=first).status_code == 400
    assert client.post('/api/conversation/start', json={}, headers={**HEADERS, 'X-EasyTrip-Draft':'../bad'}).status_code == 400
    assert client.post('/api/conversation/close', json={}, headers={'X-EasyTrip-Draft':first['X-EasyTrip-Draft']}).status_code == 403


def test_long_unicode_name_can_be_saved(client, monkeypatch):
    mock_planner(monkeypatch)
    first = tab()
    client.post('/api/conversation/start', json={}, headers=first)
    client.post('/api/chat', json={'message':'Kyoto'}, headers=first)
    saved = client.post('/api/trips', json={'name':'旅行' * 50}, headers=first)
    assert saved.status_code == 201
    assert saved.json['name'] == '旅行' * 50
    assert len(saved.json['id'].encode('utf-8')) < 255
