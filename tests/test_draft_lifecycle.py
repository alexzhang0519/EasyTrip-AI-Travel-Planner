from Backend.app.api.routes import chat as routes
from Backend.app.memory.database import connection
from test_app import app, client, HEADERS


def test_reset_deletes_only_current_draft_and_preserves_saved_trip(client, app, monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'test-only')
    monkeypatch.setattr(routes, 'run_agent', lambda messages: messages + [
        {'role': 'assistant', 'content': 'A draft plan'}])
    original = client.post('/api/chat', json={'message': 'Kyoto'}, headers=HEADERS).json
    saved = client.post('/api/trips', json={'name': 'Keep this trip'}, headers=HEADERS).json
    other = app.test_client()
    other.post('/api/chat', json={'message': 'Paris'}, headers=HEADERS)
    with client.session_transaction() as session:
        draft_id = session['conversation_id']
    assert client.post('/api/conversation/reset', json={}, headers=HEADERS).status_code == 200
    assert client.get('/api/conversation').json == {'messages': [], 'pois': []}
    with app.app_context(), connection() as db:
        assert db.execute('SELECT data FROM conversations WHERE id=?', (draft_id,)).fetchone() is None
        assert db.execute('SELECT COUNT(*) FROM conversations').fetchone()[0] == 1
    assert other.get('/api/conversation').json['messages'][0]['content'] == 'Paris'
    assert len(client.get('/api/trips').json['trips']) == 1
    loaded = client.post('/api/trips/' + saved['id'] + '/load', json={}, headers=HEADERS)
    assert loaded.json == original
