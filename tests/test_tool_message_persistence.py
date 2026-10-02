import json
from openai.types.chat import ChatCompletionMessage
from Backend.app.memory import trips as persistence
from Backend.app.api.routes import chat as routes
from test_app import app, client, HEADERS


def tool_message():
    return ChatCompletionMessage(role='assistant', content=None, tool_calls=[{
        'id': 'call_places', 'type': 'function',
        'function': {'name': 'search_pois', 'arguments': '{"lat":35,"lon":135}'}}])


def test_clean_serialized_tool_call_without_content():
    message = tool_message().model_dump(exclude_none=True)
    assert 'content' not in message
    assert persistence._clean_messages([
        {'role': 'system'}, message, {'role': 'tool', 'content': '[]'},
        {'role': 'user', 'content': 'Kyoto'},
        {'role': 'assistant', 'content': 'Visit a garden.'}
    ]) == [{'role': 'user', 'content': 'Kyoto'}, {'role': 'assistant', 'content': 'Visit a garden.'}]


def test_sdk_tool_messages_survive_chat_save_and_reload(client, monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'test-only')
    def fake_agent(messages):
        return messages + [tool_message(), {'role':'tool','tool_call_id':'call_places',
            'content':json.dumps([{'name':'Garden','lat':35.,'lon':135.,'kind':'sight'}])},
            ChatCompletionMessage(role='assistant',content='Visit Garden.')]
    monkeypatch.setattr(routes,'run_agent',fake_agent)
    reply=client.post('/api/chat',json={'message':'Kyoto'},headers=HEADERS)
    assert reply.status_code==200
    assert reply.json['messages'][-1]['content']=='Visit Garden.'
    assert reply.json['messages'][-1]['places'][0]['name']=='Garden'
    assert reply.json['pois'][0]['name']=='Garden'
    assert [m['role'] for m in reply.json['messages']]==['user','assistant']
    saved=client.post('/api/trips',json={'name':'Kyoto'},headers=HEADERS)
    assert saved.status_code==201
    loaded=client.post('/api/trips/'+saved.json['id']+'/load',json={},headers=HEADERS)
    assert loaded.status_code==200
    assert loaded.json==reply.json
