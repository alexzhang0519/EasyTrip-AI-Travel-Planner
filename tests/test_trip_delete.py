from pathlib import Path
from Backend.app.api.routes import chat as routes
from Backend.app.memory import trips
from test_app import app, client, HEADERS


def test_plan_save_reopen_delete_lifecycle(client, monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'test-only')
    monkeypatch.setattr(routes, 'run_agent', lambda messages: messages + [
        {'role': 'assistant', 'content': 'Day 1: Garden, then lunch.'}])
    plan = client.post('/api/trips/plan', json={'destination': 'Kyoto'}, headers=HEADERS)
    assert plan.status_code == 200
    saved = client.post('/api/trips', json={'name': 'Kyoto day'}, headers=HEADERS)
    assert saved.status_code == 201
    trip_id = saved.json['id']
    second = client.post('/api/trips', json={'name': 'Keep me'}, headers=HEADERS).json['id']
    client.post('/api/conversation/reset', json={}, headers=HEADERS)
    loaded = client.post(f'/api/trips/{trip_id}/load', json={}, headers=HEADERS)
    assert loaded.json == plan.json
    client.post(f'/api/trips/{trip_id}/feedback', json={'rating': 'down', 'comment': 'Remove this feedback'}, headers=HEADERS)
    assert client.post(f'/api/trips/{trip_id}/delete', json={}, headers=HEADERS).status_code == 200
    assert not (Path(trips.TRIPS_DIR) / trip_id).exists()
    assert [t['id'] for t in client.get('/api/trips').json['trips']] == [second]
    assert trips.collect_feedback_notes() == []
    assert client.post(f'/api/trips/{trip_id}/load', json={}, headers=HEADERS).status_code == 404
    assert client.post(f'/api/trips/{trip_id}/delete', json={}, headers=HEADERS).status_code == 404
    # Deleting a saved snapshot leaves the already opened working copy alone.
    assert client.get('/api/conversation').json == plan.json
    assert client.post(f'/api/trips/{second}/delete', json={}, headers=HEADERS).status_code == 200
    assert client.get('/api/trips').json == {'trips': []}


def test_delete_rejects_cross_site_invalid_and_symlink_targets(client, tmp_path):
    assert client.post('/api/trips/test.json/delete', json={}).status_code == 403
    assert client.post('/api/trips/test.json/delete', json={}, headers={**HEADERS, 'Origin': 'https://other.example'}).status_code == 403
    assert client.post('/api/trips/secret.env/delete', json={}, headers=HEADERS).status_code == 400
    outside = tmp_path / 'outside.json'
    outside.write_text('{}')
    directory = Path(trips.TRIPS_DIR)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'link.json').symlink_to(outside)
    assert client.post('/api/trips/link.json/delete', json={}, headers=HEADERS).status_code == 404
    assert outside.exists()
