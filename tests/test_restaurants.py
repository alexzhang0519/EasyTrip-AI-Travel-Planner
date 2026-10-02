import pytest
import requests
from Backend.app.services import restaurants as service
from Backend.app.services import geocoding
from Backend.app.api.routes import map as routes
from test_app import client, app, HEADERS

@pytest.fixture(autouse=True)
def clean_cache(monkeypatch):
    service._cache.clear()
    geocoding._cache.clear()
    monkeypatch.setattr(service, '_next_request', 0)
    monkeypatch.setattr(geocoding, '_next_request', 0)


def response(data):
    class Reply:
        def raise_for_status(self): pass
        def json(self): return data
    return Reply()


def sample():
    return {'elements': [
        {'type': 'way', 'id': 1, 'center': {'lat': 40.001, 'lon': -74},
         'tags': {'name': 'Garden Cafe', 'amenity': 'cafe', 'cuisine': 'coffee_shop;italian',
                  'diet:vegetarian': 'yes', 'opening_hours': 'Mo-Fr 09:00-17:00'}},
        {'type': 'node', 'id': 2, 'lat': 40.002, 'lon': -74,
         'tags': {'name': 'Ramen Place', 'amenity': 'restaurant', 'cuisine': 'ramen'}},
        {'type': 'relation', 'id': 3, 'center': {'lat': 40.003, 'lon': -74},
         'tags': {'name': 'Food Hall', 'amenity': 'food_court'}},
        {'type': 'node', 'id': 4, 'lat': 40, 'lon': -74, 'tags': {'amenity': 'restaurant'}},
    ]}


def test_shapes_filters_and_cached_search(monkeypatch):
    calls=[]
    def post(url, **kwargs):
        calls.append((url, kwargs))
        assert 'Authorization' not in kwargs['headers']
        assert 'nwr[' in kwargs['data']['data']
        return response(sample())
    monkeypatch.setattr(service.requests, 'post', post)
    places=service.search_restaurants(40, -74)
    assert [p['name'] for p in places] == ['Garden Cafe', 'Ramen Place', 'Food Hall']
    assert places[0]['url'] == 'https://www.openstreetmap.org/way/1'
    assert places[0]['opening_hours'] == 'Mo-Fr 09:00-17:00'
    assert 'rating' not in places[0] and 'price' not in places[0]
    assert service.search_restaurants(40,-74,cuisine='ITALIAN')[0]['name']=='Garden Cafe'
    assert service.search_restaurants(40,-74,cuisine='vegetarian')[0]['name']=='Garden Cafe'
    assert service.search_restaurants(40,-74,cuisine='vegan')==[]
    assert len(calls)==1
    places[0]['name']='Modified'
    assert service.search_restaurants(40,-74)[0]['name']=='Garden Cafe'


def test_free_api_without_any_keys(client, monkeypatch):
    monkeypatch.setattr(routes,'geocode_city',lambda city:{'lat':40,'lon':-74})
    monkeypatch.setattr(service.requests,'post',lambda *args,**kwargs:response(sample()))
    result=client.post('/api/restaurants',json={'city':'New York','radius':1500},headers=HEADERS)
    assert result.status_code==200
    assert len(result.json['restaurants'])==3
    assert result.json['restaurants'][0]['source']=='openstreetmap'
    assert client.get('/api/status').json['restaurants_ready']


@pytest.mark.parametrize('radius', [True, '1500', 999999, -1])
def test_bad_radius_rejected_before_network(client, radius, monkeypatch):
    monkeypatch.setattr(routes,'geocode_city',lambda city:pytest.fail('Should not call geocoder'))
    assert client.post('/api/restaurants',json={'city':'Kyoto','radius':radius},headers=HEADERS).status_code==400


def test_upstream_failure_no_paid_fallback(client, monkeypatch):
    monkeypatch.setattr(routes,'geocode_city',lambda city:{'lat':40,'lon':-74})
    def fail(*args, **kwargs): raise requests.Timeout()
    monkeypatch.setattr(service.requests,'post',fail)
    result=client.post('/api/restaurants',json={'city':'New York'},headers=HEADERS)
    assert result.status_code==502
    assert 'no paid fallback' in result.json['error']


def test_partial_overpass_response_is_failure(monkeypatch):
    monkeypatch.setattr(service.requests,'post',lambda *a,**k:response({'elements':[], 'remark':'timed out'}))
    assert service.search_restaurants(40,-74) is None


def test_no_results_distinct_from_failure(monkeypatch):
    monkeypatch.setattr(service.requests,'post',lambda *a,**k:response({'elements':[]}))
    assert service.search_restaurants(40,-74)==[]


def test_geocoder_caches_normalized_city(monkeypatch):
    calls=[]
    def get(*args,**kwargs):
        calls.append(kwargs)
        return response([{'display_name':'Kyoto','lat':'35','lon':'135'}])
    monkeypatch.setattr(geocoding.requests,'get',get)
    assert geocoding.geocode_city(' Kyoto ')['lat']==35
    assert geocoding.geocode_city('KYOTO')['lon']==135
    assert len(calls)==1
