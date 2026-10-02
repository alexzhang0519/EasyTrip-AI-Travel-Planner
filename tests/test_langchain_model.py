"""Offline adapter tests: no live OpenAI calls."""
import json
import sys
from types import SimpleNamespace
import pytest
from openai.types.chat import ChatCompletionMessage
from Backend.app.agents.langchain_model import invoke_model, make_model


class FakeModel:
    def __init__(self, answer):
        self.answer, self.bound, self.messages = answer, None, None

    def bind_tools(self, tools):
        self.bound = tools
        return self

    def invoke(self, messages):
        self.messages = messages
        return self.answer


def test_tool_roundtrip_retains_ids_and_removes_presentation_metadata():
    model = FakeModel(SimpleNamespace(content="", tool_calls=[{
        "name": "geocode_city", "args": {"city": "東京"}, "id": "call_2"}]))
    prior = ChatCompletionMessage(role="assistant", content=None, tool_calls=[{
        "id": "call_1", "type": "function", "function": {
            "name": "geocode_city", "arguments": '{"city":"Kyoto"}'}}])
    messages = [
        {"role": "user", "content": "Kyoto", "places": [{"name": "private"}]}, prior,
        {"role": "tool", "tool_call_id": "call_1", "content": '{"lat":35}', "error": False},
        {"role": "assistant", "content": "Earlier plan", "context": {"private": True}},
    ]
    schemas = [{"type": "function", "function": {"name": "geocode_city"}}]
    result = invoke_model(model, messages, schemas)
    assert model.bound is schemas
    assert model.messages[0] == {"role": "user", "content": "Kyoto"}
    assert model.messages[1]["tool_calls"][0]["id"] == "call_1"
    assert model.messages[2] == {"role": "tool", "tool_call_id": "call_1", "content": '{"lat":35}'}
    assert model.messages[3] == {"role": "assistant", "content": "Earlier plan"}
    assert result["tool_calls"][0]["id"] == "call_2"
    assert json.loads(result["tool_calls"][0]["function"]["arguments"]) == {"city": "東京"}
    assert messages[0]["places"]


def test_final_text_blocks_exclude_reasoning():
    model = FakeModel(SimpleNamespace(content=[
        {"type": "reasoning", "text": "private reasoning"},
        {"type": "text", "text": "Day 1"}, "Visit the garden.",
    ], tool_calls=[]))
    assert invoke_model(model, [], []) == {
        "role": "assistant", "content": "Day 1\nVisit the garden.", "tool_calls": []}
    assert model.bound is None


def test_invalid_arguments_survive_for_executor_error_response():
    model = FakeModel(SimpleNamespace(content="", tool_calls=[], invalid_tool_calls=[{
        "id": "bad_1", "name": "geocode_city", "args": "not-json", "error": "parse error"}]))
    assert invoke_model(model, [], [])["tool_calls"][0] == {
        "id": "bad_1", "type": "function", "function": {
            "name": "geocode_city", "arguments": "not-json"}}


def test_model_creation_uses_official_endpoint(monkeypatch):
    captured = {}
    def factory(**kwargs):
        captured.update(kwargs)
        return "model"
    monkeypatch.setitem(sys.modules, "langchain_openai", SimpleNamespace(ChatOpenAI=factory))
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://untrusted.invalid")
    assert make_model() == "model"
    assert captured == {"api_key": "test-only", "model": "test-model",
                        "base_url": "https://api.openai.com/v1", "timeout": 60.0,
                        "max_retries": 2, "use_responses_api": False}


def test_missing_key_does_not_load_langchain(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setitem(sys.modules, "langchain_openai", None)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        make_model()


def test_real_langchain_serializes_legacy_tool_history_without_network():
    import httpx
    from langchain_openai import ChatOpenAI
    requests = []
    def handler(request):
        data = json.loads(request.content)
        requests.append(data)
        assert request.url.host == "api.openai.com"
        assert request.url.path == "/v1/chat/completions"
        if len(requests) == 1:
            assert data["tools"][0]["function"]["name"] == "geocode_city"
            message = {"role": "assistant", "content": None, "tool_calls": [{
                "id": "roundtrip_1", "type": "function", "function": {
                    "name": "geocode_city", "arguments": '{"city":"Kyoto"}'}}]}
        else:
            assert data["messages"][-1]["tool_call_id"] == "roundtrip_1"
            assert data["messages"][-2]["tool_calls"][0]["id"] == "roundtrip_1"
            assert "places" not in data["messages"][0]
            message = {"role": "assistant", "content": "Your Kyoto plan."}
        return httpx.Response(200, json={"id": "chatcmpl-test", "object": "chat.completion",
            "created": 0, "model": "gpt-4.1-mini", "choices": [{"index": 0,
            "message": message, "finish_reason": "tool_calls" if len(requests) == 1 else "stop"}]})
    model = ChatOpenAI(api_key="test-only", model="gpt-4.1-mini",
        base_url="https://api.openai.com/v1", use_responses_api=False,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)), max_retries=0)
    history = [{"role": "user", "content": "Kyoto", "places": [{"name": "old"}]}]
    tools = [{"type": "function", "function": {"name": "geocode_city",
              "parameters": {"type": "object", "properties": {"city": {"type": "string"}},
                             "required": ["city"]}}}]
    call = invoke_model(model, history, tools)
    history.extend([call, {"role": "tool", "tool_call_id": "roundtrip_1", "content": '{"lat":35}'}])
    assert invoke_model(model, history, tools)["content"] == "Your Kyoto plan."
    assert len(requests) == 2
