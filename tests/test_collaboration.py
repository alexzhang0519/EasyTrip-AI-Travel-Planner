"""Network-free collaboration and API persistence checks."""
import json
from contextvars import ContextVar

import pytest
from Backend.app.agents import collaboration
from Backend.app.services.evidence import flatten_evidence, weather_reports, agent_reports
from Backend.app.api.routes import chat as routes
from test_app import app, client, HEADERS

WEATHER = {'status': 'partial', 'source': 'Open-Meteo', 'source_url': 'https://open-meteo.com/',
    'timezone': 'Asia/Tokyo', 'fetched_at': '2026-10-02T00:00:00+00:00',
    'requested_start_date': '2026-10-17', 'requested_days': 3, 'forecast_horizon_days': 16,
    'daily': [{'date': '2026-10-17', 'temperature_min_c': 10, 'temperature_max_c': 20,
               'precipitation_probability_max': 40, 'weather_code': 3}],
    'warnings': ['Only one requested day is within forecast range.']}


def fake_loop(fail=(), record=None):
    def run(messages, *, tools, functions, max_turns, agent_name, structured=False):
        if record is not None:
            record.append((agent_name, tools, functions, max_turns))
        if agent_name in fail:
            raise RuntimeError('simulated unavailable branch')
        if agent_name == 'Coordinating planner':
            return messages + [{'role': 'assistant', 'content': 'Day 1: Visit Garden. Weather only covers one day.'}]
        if agent_name == 'Weather adviser':
            return messages + [{'role': 'tool', 'content': json.dumps(WEATHER)},
                               {'role': 'assistant', 'content': 'Forecast is partial.'}]
        return messages + [
            {'role': 'assistant', 'tool_calls': [{'id': 'search', 'function': {
                'name': 'search_pois', 'arguments': '{"lat":35,"lon":135}'}}]},
            {'role': 'tool', 'content': '{"name":"Kyoto, Japan","lat":35,"lon":135}'},
            {'role': 'tool', 'tool_call_id': 'search', 'content': '[{"name":"Garden","lat":35,"lon":135}]'},
            {'role': 'assistant', 'content': 'Garden is a real returned venue.'}]
    return run


def initial():
    return [{'role': 'system', 'content': 'Plan carefully.'}, {'role': 'user', 'content': 'Kyoto October 17 for 3 days.'}]


def test_specialist_permissions_turn_limits_and_context(monkeypatch):
    record = []
    marker = ContextVar('test_marker', default='missing')
    token = marker.set('request-context')
    runner = fake_loop(record=record)
    def checked(*args, **kwargs):
        assert marker.get() == 'request-context'
        return runner(*args, **kwargs)
    monkeypatch.setattr(collaboration, 'run_loop', checked)
    try:
        result = collaboration.run_collaboration(initial())
    finally:
        marker.reset(token)
    by_agent = {name: (tools, funcs, turns) for name, tools, funcs, turns in record}
    for name, (allowed, _) in collaboration.SPECIALISTS.items():
        tools, funcs, turns = by_agent[name]
        assert set(funcs) == allowed
        assert {t['function']['name'] for t in tools} == allowed
        assert turns == 4
    assert by_agent['Coordinating planner'] == ([], {}, 1)
    assert result[-1]['role'] == 'assistant'
    assert weather_reports(flatten_evidence(result)) == [dict(WEATHER, location="Kyoto, Japan")]
    assert len(agent_reports(result)) == 2


@pytest.mark.parametrize('failed', ['Place researcher', 'Weather adviser'])
def test_one_branch_failure_keeps_other_evidence(monkeypatch, failed):
    monkeypatch.setattr(collaboration, 'run_loop', fake_loop(fail={failed}))
    result = collaboration.run_collaboration(initial())
    assert not result[-1].get('error')
    reports = {item['agent']: item for item in agent_reports(result)}
    assert reports[failed]['status'] == 'unavailable'
    assert sum(r['status'] == 'complete' for r in reports.values()) == 1


def test_both_fail_do_not_synthesize(monkeypatch):
    record = []
    monkeypatch.setattr(collaboration, 'run_loop', fake_loop(fail=set(collaboration.SPECIALISTS), record=record))
    result = collaboration.run_collaboration(initial())
    assert result[-1]['error'] is True
    assert len(record) == 2


def test_api_preserves_weather_agents_and_places_across_save_load(client, monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'test-only')
    monkeypatch.setattr(collaboration, 'run_loop', fake_loop())
    response = client.post('/api/chat', json={'message': 'Kyoto October 17 for 3 days.', 'collaborate': True}, headers=HEADERS)
    assert response.status_code == 200
    answer = response.json['messages'][-1]
    assert answer['weather'] == [dict(WEATHER, location="Kyoto, Japan")]
    assert len(answer['agents']) == 2
    assert answer['places'][0]['location'] == 'Kyoto, Japan'
    assert all(m['role'] in ('assistant', 'user') for m in response.json['messages'])
    saved = client.post('/api/trips', json={'name': 'Weather evidence'}, headers=HEADERS)
    assert saved.status_code == 201
    client.post('/api/conversation/reset', json={}, headers=HEADERS)
    loaded = client.post('/api/trips/' + saved.json['id'] + '/load', json={}, headers=HEADERS)
    assert loaded.json == response.json


def test_failed_collaboration_keeps_previous_plan(client, monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'test-only')
    monkeypatch.setattr(collaboration, 'run_loop', fake_loop())
    old = client.post('/api/chat', json={'message': 'Kyoto', 'collaborate': True}, headers=HEADERS).json
    monkeypatch.setattr(collaboration, 'run_loop', fake_loop(fail=set(collaboration.SPECIALISTS)))
    failed = client.post('/api/chat', json={'message': 'Try another city', 'collaborate': True}, headers=HEADERS)
    assert failed.status_code == 502
    assert client.get('/api/conversation').json == old
    assert client.get('/api/planning-status').json['stage'] == 'idle'


def test_collaborate_requires_boolean(client, monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'test-only')
    response = client.post('/api/chat', json={'message': 'Kyoto', 'collaborate': 'true'}, headers=HEADERS)
    assert response.status_code == 400
