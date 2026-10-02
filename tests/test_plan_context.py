import json
from Backend.routes import api as routes
from Backend.Services import progress
from Backend.Services.places import extract_pois
from Backend.Services.plan_sources import collect_sources
from test_app import app, client, HEADERS


def results(city, lat):
    return [
        {'role':'tool','content':json.dumps({'name':city,'lat':lat,'lon':10})},
        {'role':'tool','content':json.dumps([{'name':'City Museum','lat':lat,'lon':10}])},
        {'role':'assistant','content':'Day 1: Museums\nMorning: Visit City Museum.'}]


def test_cities_do_not_change_old_links_and_survive_save(client, monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','test-only')
    count = 0
    def agent(messages):
        nonlocal count
        assert all(set(m) <= {'role','content'} for m in messages)
        count += 1
        return messages + results('Kyoto, Japan' if count == 1 else 'Paris, France', count)
    monkeypatch.setattr(routes,'run_agent',agent)
    client.post('/api/chat',json={'message':'Kyoto'},headers=HEADERS)
    response = client.post('/api/chat',json={'message':'Paris'},headers=HEADERS).json
    answers = [m for m in response['messages'] if m['role']=='assistant']
    assert answers[0]['places'][0]['location']=='Kyoto, Japan'
    assert answers[1]['places'][0]['location']=='Paris, France'
    saved=client.post('/api/trips',json={'name':'Two cities'},headers=HEADERS).json
    client.post('/api/conversation/reset',json={},headers=HEADERS)
    loaded=client.post('/api/trips/'+saved['id']+'/load',json={},headers=HEADERS).json
    assert loaded == response


def test_failed_plan_preserves_history_and_progress_is_private(client, app, monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','test-only')
    other=app.test_client()
    def agent(messages):
        progress.report('Searching free place listings…')
        assert client.get('/api/planning-status').json['stage']=='Searching free place listings…'
        assert other.get('/api/planning-status').json['stage']=='idle'
        return messages + [{'role':'assistant','content':'Try again later','error':True}]
    monkeypatch.setattr(routes,'run_agent',agent)
    response=client.post('/api/chat',json={'message':'Kyoto'},headers=HEADERS)
    assert response.status_code==502
    assert client.get('/api/conversation').json['messages']==[]
    assert client.get('/api/planning-status').json['stage']=='idle'


def test_multiple_geocodes_match_search_centers():
    messages=[{'role':'assistant','tool_calls':[
        {'id':'a','function':{'name':'search_pois','arguments':'{"lat":1,"lon":10}'}},
        {'id':'b','function':{'name':'search_pois','arguments':'{"lat":2,"lon":10}'}}]},
        results('Kyoto, Japan',1)[0], results('Paris, France',2)[0],
        dict(results('Kyoto, Japan',1)[1],tool_call_id='a'),
        dict(results('Paris, France',2)[1],tool_call_id='b')]
    assert [p['location'] for p in extract_pois(messages)]==['Kyoto, Japan','Paris, France']


def test_source_only_when_guide_succeeds():
    call={'role':'assistant','tool_calls':[{'id':'rag','function':{'name':'lookup_travel_info','arguments':'{"city":"Kyoto"}'}}]}
    failed={'role':'tool','tool_call_id':'rag','content':json.dumps('No travel guide found for Kyoto.')}
    assert collect_sources([call,failed],[])==[]
    success=dict(failed,content=json.dumps('Kyoto gardens guide'))
    assert collect_sources([call,success],[])[0]['url']=='https://en.wikivoyage.org/wiki/Kyoto'
