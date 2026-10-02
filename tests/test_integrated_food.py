"""Exercise restaurant tool dispatch, combined plans, and persistence without paid calls."""
import json
from urllib.parse import urlparse, parse_qs
import pytest
from Backend.app.agents import core, collaboration
from Backend.app.services import restaurants
from test_app import app, client, HEADERS

FOOD = {'name': 'Garden Kitchen', 'lat': 35.01, 'lon': 135.01,
        'kind': 'food', 'source': 'openstreetmap', 'vegetarian': 'yes',
        'address': '12 Garden Street'}
PLAN = {'summary': 'Sights and food together.', 'days': [{'day': 1,
    'title': 'Garden district', 'activities': [
        {'period': 'Morning', 'description': 'Visit the garden.',
         'place': {'name': 'City Garden', 'city': 'Kyoto, Japan', 'address': None}},
        {'period': 'Lunch', 'description': 'Nearby vegetarian option; confirm dietary needs.',
         'place': {'name': FOOD['name'], 'city': 'Kyoto, Japan', 'address': FOOD['address']}},
        {'period': 'Dinner', 'description': 'Meal break; no second suitable listing found.', 'place': None}]}],
    'warnings': ['Dinner venue needs checking.']}

@pytest.mark.parametrize('collaborate', [False, True])
def test_meals_researched_linked_and_saved_in_both_modes(client, monkeypatch, collaborate):
    monkeypatch.setenv('OPENAI_API_KEY', 'test-only')
    monkeypatch.setattr(core, 'client', object())
    monkeypatch.setitem(core.TOOL_FUNCTIONS, 'geocode_city', lambda city: {'name': 'Kyoto, Japan', 'lat': 35, 'lon': 135})
    monkeypatch.setitem(core.TOOL_FUNCTIONS, 'search_pois', lambda lat, lon: [
        {'name': 'City Garden', 'lat': 35.01, 'lon': 135.01, 'kind': 'sight'}])
    searches = []
    def food(lat, lon, radius, *, cuisine, limit):
        searches.append((lat, lon, cuisine))
        return [FOOD]
    # Keep the actual agent wrapper and core dispatcher, replace only network service.
    monkeypatch.setattr(restaurants, 'search_restaurants', food)
    def model(model, messages, tools, response_schema=None):
        if response_schema:
            return {'role': 'assistant', 'content': json.dumps(PLAN)}
        names = {t['function']['name'] for t in tools}
        if 'search_restaurants' not in names:
            return {'role': 'assistant', 'content': 'Weather unavailable.'}
        done = [c['function']['name'] for m in messages for c in m.get('tool_calls', [])]
        steps = [('geocode_city', {'city': 'Kyoto'}),
                 ('search_pois', {'lat': 35, 'lon': 135}),
                 ('search_restaurants', {'lat': 35.01, 'lon': 135.01, 'cuisine': 'vegetarian'})]
        if len(done) < len(steps):
            name, args = steps[len(done)]
            return {'role': 'assistant', 'content': '', 'tool_calls': [
                {'id': name, 'type': 'function', 'function': {'name': name, 'arguments': json.dumps(args)}}]}
        assert any(FOOD['name'] in m.get('content', '') for m in messages if m['role'] == 'tool')
        return {'role': 'assistant', 'content': 'Garden and nearby Garden Kitchen; dinner match missing.'}
    monkeypatch.setattr(core, 'invoke_model', model)
    response = client.post('/api/trips/plan', json={'destination': 'Kyoto', 'days': 1,
        'food_preferences': 'vegetarian', 'collaborate': collaborate}, headers=HEADERS)
    assert response.status_code == 200, response.json
    assert searches == [(35.01, 135.01, 'vegetarian')]
    assert 'Food preferences and dietary needs: vegetarian' in response.json['messages'][0]['content']
    answer = response.json['messages'][-1]
    meals = answer['itinerary']['days'][0]['activities'][1:]
    assert parse_qs(urlparse(meals[0]['place']['map_url']).query)['query'] == [
        'Garden Kitchen, 12 Garden Street, Kyoto, Japan']
    assert meals[1]['place'] is None
    assert {p['name'] for p in answer['places']} == {'City Garden', 'Garden Kitchen'}
    saved = client.post('/api/trips', json={'name': 'Sights and meals'}, headers=HEADERS)
    client.post('/api/conversation/reset', json={}, headers=HEADERS)
    loaded = client.post('/api/trips/' + saved.json['id'] + '/load', json={}, headers=HEADERS)
    assert loaded.json == response.json


def test_food_preferences_length_validated(client):
    response = client.post('/api/trips/plan', json={
        'destination': 'Kyoto', 'food_preferences': 'x' * 301}, headers=HEADERS)
    assert response.status_code == 400
