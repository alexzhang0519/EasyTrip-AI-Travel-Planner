"""Exercise real SDK request serialization without network calls or real keys."""
import json
import httpx
import pytest
from openai import OpenAI
from langchain_openai import ChatOpenAI
from Backend.app.agents import core


def embedding_sdk(handler):
    return OpenAI(api_key='test-only', base_url='https://api.openai.com/v1',
                  http_client=httpx.Client(transport=httpx.MockTransport(handler)), max_retries=0)


def chat_model(handler):
    return ChatOpenAI(api_key='test-only', model=core.MODEL,
                      base_url='https://api.openai.com/v1', use_responses_api=False,
                      http_client=httpx.Client(transport=httpx.MockTransport(handler)), max_retries=0)


def test_openai_chat_tool_roundtrip(monkeypatch):
    requests = []
    def handler(request):
        assert request.url.host == 'api.openai.com'
        assert request.url.path == '/v1/chat/completions'
        assert request.headers['authorization'] == 'Bearer test-only'
        data = json.loads(request.content)
        requests.append(data)
        if len(requests) == 1:
            message = {'role': 'assistant', 'content': None, 'tool_calls': [
                {'id': 'call_1', 'type': 'function', 'function': {
                    'name': 'geocode_city', 'arguments': '{"city":"Kyoto"}'}}]}
        else:
            assert data['messages'][-1]['tool_call_id'] == 'call_1'
            assert json.loads(data['messages'][-1]['content'])['lat'] == 35
            message = {'role': 'assistant', 'content': json.dumps({'summary':'Here is your Kyoto plan.','days':[],'warnings':[]})}
        return httpx.Response(200, json={'id': 'chatcmpl-test', 'object': 'chat.completion',
            'created': 0, 'model': data['model'], 'choices': [{'index': 0, 'message': message,
            'finish_reason': 'tool_calls' if len(requests) == 1 else 'stop'}]})
    monkeypatch.setattr(core, 'client', chat_model(handler))
    monkeypatch.setitem(core.TOOL_FUNCTIONS, 'geocode_city', lambda city: {'lat': 35, 'lon': 135})
    result = core.run_agent([{'role': 'user', 'content': 'Kyoto'}])
    assert result[-1]['content'] == 'Here is your Kyoto plan.'
    assert len(requests) == 3
    assert requests[0]['model'] == core.MODEL
    assert requests[0]['tools']
    assert requests[-1]['response_format']['type'] == 'json_schema'


def test_missing_openai_key_does_not_use_old_gemini_key(monkeypatch):
    monkeypatch.setattr(core, 'client', None)
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.setenv('GEMINI_API_KEY', 'unused-old-key')
    assert 'OPENAI_API_KEY' in core.run_agent([])[-1]['content']


def test_embedding_sdk_and_real_faiss_retrieval(monkeypatch):
    pytest.importorskip('faiss')
    from Backend.app.rag.base import embeddings as rag
    from Backend.app.rag.pre_data.index import build_index
    from Backend.app.rag.retriever.vector import retrieve
    requests = []
    def handler(request):
        assert request.url.host == 'api.openai.com'
        assert request.url.path == '/v1/embeddings'
        data = json.loads(request.content)
        requests.append(data)
        assert data['model'] == rag.EMBED_MODEL
        assert data['encoding_format'] == 'float'
        vectors = [[1., 0.] if 'garden' in text.lower() else [0., 1.] for text in data['input']]
        return httpx.Response(200, json={'object': 'list', 'model': data['model'], 'data': [
            {'object': 'embedding', 'index': i, 'embedding': vector}
            for i, vector in reversed(list(enumerate(vectors)))],
            'usage': {'prompt_tokens': 10, 'total_tokens': 10}})
    monkeypatch.setattr(rag, 'client', embedding_sdk(handler))
    chunks = ['Quiet gardens', 'Nightlife and clubs']
    index = build_index(chunks)
    assert retrieve('garden walks', chunks, index, top_k=3) == chunks
    assert len(requests) == 2


def test_openai_authentication_error_is_handled(monkeypatch):
    monkeypatch.setattr(core, 'client', chat_model(lambda request: httpx.Response(401, json={
        'error': {'message': 'Invalid key', 'type': 'invalid_request_error', 'code': 'invalid_api_key'}})))
    result = core.run_agent([{'role': 'user', 'content': 'Kyoto'}])
    assert 'API configuration' in result[-1]['content']
