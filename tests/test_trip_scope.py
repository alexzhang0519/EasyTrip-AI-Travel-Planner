import json
from pathlib import Path
from Backend.app.api.routes import chat as routes
from Backend.app.memory import trips
from Backend.app.memory.trip_scope import current_trip_messages
from test_app import app, client, HEADERS


def test_create_two_trips_save_and_load_without_cross_trip_history(client, monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','test-only')
    histories=[]
    def agent(messages):
        histories.append(messages.copy())
        return messages + [{'role':'assistant','content':'Plan: '+messages[-1]['content']}]
    monkeypatch.setattr(routes,'run_agent',agent)
    client.post('/api/chat',json={'message':'Boston','new_trip':True},headers=HEADERS)
    first=client.post('/api/trips',json={'name':'Boston'},headers=HEADERS).json['id']
    created=client.post('/api/chat',json={'message':'New York','new_trip':True},headers=HEADERS)
    assert created.status_code==200
    assert not any('Boston' in m['content'] for m in histories[-1])
    assert len(created.json['messages'])==2
    refined=client.post('/api/chat',json={'message':'Add nearby lunch'},headers=HEADERS)
    assert len(refined.json['messages'])==4
    assert any('New York' in m['content'] for m in histories[-1])
    second=client.post('/api/trips',json={'name':'New York'},headers=HEADERS).json['id']
    loaded_first=client.post(f'/api/trips/{first}/load',json={},headers=HEADERS)
    assert len(loaded_first.json['messages'])==2
    assert 'New York' not in json.dumps(loaded_first.json)
    loaded_second=client.post(f'/api/trips/{second}/load',json={},headers=HEADERS)
    assert loaded_second.json==refined.json
    assert 'Boston' not in json.dumps(loaded_second.json)


def test_legacy_mixed_snapshot_load_keeps_latest_trip_and_followups_without_rewriting(tmp_path):
    def request(city):
        return {'role':'user','content':f'Plan a 2-day trip to {city}. Start date: not set. Pace: Relaxed. Getting around: Walking. Interests: art. Budget and preferences: flexible.'}
    old=[request('Boston'), {'role':'assistant','content':'Boston plan'}, request('New York'),
         {'role':'assistant','content':'New York plan'}, {'role':'user','content':'Add lunch'},
         {'role':'assistant','content':'New York lunch'}]
    path=tmp_path/'mixed.json'
    path.write_text(json.dumps({'name':'New York','messages':old,'pois':[]}))
    before=path.read_bytes()
    assert trips.load_trip(str(path))['messages']==old[2:]
    assert path.read_bytes()==before
    assert current_trip_messages([{'role':'user','content':'Compare Boston and New York'}])==[{'role':'user','content':'Compare Boston and New York'}]


def test_failed_new_trip_preserves_previous_and_rejects_invalid_flag(client,monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','test-only')
    monkeypatch.setattr(routes,'run_agent',lambda messages:messages+[{'role':'assistant','content':'Old plan'}])
    old=client.post('/api/chat',json={'message':'Boston','new_trip':True},headers=HEADERS).json
    monkeypatch.setattr(routes,'run_agent',lambda messages:messages+[{'role':'assistant','content':'Unavailable','error':True}])
    assert client.post('/api/chat',json={'message':'Paris','new_trip':True},headers=HEADERS).status_code==502
    assert client.get('/api/conversation').json==old
    assert client.post('/api/chat',json={'message':'Paris','new_trip':'true'},headers=HEADERS).status_code==400
