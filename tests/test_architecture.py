import json
from urllib.parse import urlparse, parse_qs
import pytest
from pydantic import ValidationError
from Backend.app.services.itinerary import normalize_plan
from Backend.app.api.routes import chat as routes
from Backend.app.graph.workflow import build_workflow
from test_app import app, client, HEADERS

PLAN = {'summary':'A relaxed visit.','days':[{'day':1,'title':'Museums','activities':[
    {'period':'Morning','description':'Explore the collection.','place':{'name':'City Museum','city':'Kyoto, Japan','address':None}},
    {'period':'Afternoon','description':'Take a break.','place':None}]}],'warnings':['Opening hours need checking.']}

def test_map_link_comes_from_structured_place_not_description():
    text, plan = normalize_plan(json.dumps(PLAN))
    place = plan['days'][0]['activities'][0]['place']
    assert parse_qs(urlparse(place['map_url']).query)['query']==['City Museum, Kyoto, Japan']
    assert '[City Museum]' in text
    assert 'City Museum' not in PLAN['days'][0]['activities'][0]['description']
    assert plan['days'][0]['activities'][1]['place'] is None

@pytest.mark.parametrize('change',['missing_city','duplicate_day','invalid_day','extra_field'])
def test_invalid_structured_plans_are_rejected(change):
    plan=json.loads(json.dumps(PLAN))
    if change=='missing_city': plan['days'][0]['activities'][0]['place']['city']=''
    if change=='duplicate_day': plan['days'].append(plan['days'][0])
    if change=='invalid_day': plan['days'][0]['day']=0
    if change=='extra_field': plan['secret']='unexpected'
    with pytest.raises(ValueError): normalize_plan(json.dumps(plan))

def test_structured_plan_survives_save_load(client,monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','test-only')
    text,plan=normalize_plan(json.dumps(PLAN))
    monkeypatch.setattr(routes,'run_agent',lambda messages:messages+[{'role':'assistant','content':text,'itinerary':plan}])
    response=client.post('/api/chat',json={'message':'Kyoto'},headers=HEADERS)
    assert response.json['messages'][-1]['itinerary']==plan
    saved=client.post('/api/trips',json={'name':'Structured'},headers=HEADERS)
    loaded=client.post('/api/trips/'+saved.json['id']+'/load',json={},headers=HEADERS)
    assert loaded.json==response.json

def test_direct_plan_uses_fresh_history(client,monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','test-only')
    histories=[]
    def agent(messages):
        histories.append(messages.copy())
        return messages+[{'role':'assistant','content':'Done'}]
    monkeypatch.setattr(routes,'run_agent',agent)
    client.post('/api/chat',json={'message':'Old destination'},headers=HEADERS)
    response=client.post('/api/trips/plan',json={'destination':'Kyoto','days':3},headers=HEADERS)
    assert response.status_code==200
    assert not any(m.get('content')=='Old destination' for m in histories[-1])
    assert len(response.json['messages'])==2

def test_validation_error_has_trace_without_echoing_input(client):
    response=client.post('/api/chat',json={'message':{'secret':'do-not-echo'}},headers=HEADERS)
    assert response.status_code==400
    assert response.json['request_id']==response.headers['X-Request-ID']
    assert 'do-not-echo' not in response.get_data(as_text=True)
    blocked=client.post('/api/chat',json={'message':'hello'})
    assert blocked.status_code==403 and blocked.headers.get('X-Request-ID')

def test_real_graph_has_parallel_join_and_validates_result():
    seen=[]
    def researcher(name,request):
        return {'agent':name,'status':'complete','summary':'ready','evidence':[]}
    def planner(messages,reports):
        seen.extend(r['agent'] for r in reports)
        return messages+[{'role':'assistant','content':'Done'}]
    graph=build_workflow(researcher,planner)
    initial=[{'role':'user','content':'Kyoto'}]
    result=graph.invoke({'messages':initial})
    assert seen==['Place researcher','Weather adviser']
    assert result['result'][-1]['content']=='Done'
    assert len(initial)==1
    edges={(edge.source,edge.target) for edge in graph.get_graph().edges}
    assert ('prepare','places') in edges and ('prepare','weather') in edges
    assert ('places','synthesize') in edges and ('weather','synthesize') in edges
