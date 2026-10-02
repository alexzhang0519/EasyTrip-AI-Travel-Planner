"""Free restaurant discovery using public OpenStreetMap data (no API key)."""
from collections import OrderedDict
import copy
import math
import threading
import time
import unicodedata
import requests

URL = 'https://overpass-api.de/api/interpreter'
HEADERS = {'User-Agent': 'EasyTrip/1.0 (personal local travel planner)'}
CACHE_SECONDS = 15 * 60
_cache = OrderedDict()
_lock = threading.Lock()
_next_request = 0.0


def _distance(lat, lon, other_lat, other_lon):
    a, b = math.radians(lat), math.radians(other_lat)
    dlat, dlon = b - a, math.radians(other_lon - lon)
    value = math.sin(dlat / 2) ** 2 + math.cos(a) * math.cos(b) * math.sin(dlon / 2) ** 2
    return 6371000 * 2 * math.asin(min(1., math.sqrt(value)))


def _normalize(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(text)).casefold()
                   if not unicodedata.combining(c)).replace('_', ' ')


def _parse(data, lat, lon):
    places = {}
    for item in data['elements']:
        if not isinstance(item, dict):
            continue
        tags = item.get('tags') or {}
        if tags.get('amenity') not in {'restaurant', 'cafe', 'fast_food', 'food_court'}:
            continue
        name = tags.get('name') or tags.get('name:en')
        coords = item if item.get('type') == 'node' else item.get('center', {})
        y, x = coords.get('lat'), coords.get('lon')
        kind, osm_id = item.get('type'), item.get('id')
        if not name or kind not in {'node', 'way', 'relation'} or not isinstance(osm_id, int):
            continue
        if (not isinstance(y, (int, float)) or not isinstance(x, (int, float))
                or not -90 <= y <= 90 or not -180 <= x <= 180):
            continue
        cuisine = tags.get('cuisine', '').replace(';', ', ').replace('_', ' ')
        address = tags.get('addr:full') or ', '.join(filter(None, [
            ' '.join(filter(None, [tags.get('addr:housenumber'), tags.get('addr:street')])),
            tags.get('addr:city'), tags.get('addr:postcode')]))
        website = tags.get('website') or tags.get('contact:website') or ''
        place = {'name': name, 'kind': 'food', 'detail': cuisine or tags['amenity'].replace('_', ' '),
                 'cuisine': cuisine, 'lat': y, 'lon': x, 'source': 'openstreetmap',
                 'address': address, 'opening_hours': tags.get('opening_hours'),
                 'vegetarian': tags.get('diet:vegetarian'), 'vegan': tags.get('diet:vegan'),
                 'website': website if website.startswith(('https://', 'http://')) else None,
                 'url': f'https://www.openstreetmap.org/{kind}/{osm_id}',
                 'distance_m': round(_distance(lat, lon, y, x))}
        # A business can be mapped as both a point and an area; collapse near duplicates.
        identity = (_normalize(name), round(y, 4), round(x, 4))
        places.setdefault(identity, place)
    return sorted(places.values(), key=lambda p: p['distance_m'])


def search_restaurants(lat, lon, radius=1500, *, cuisine=None, limit=10):
    if (not isinstance(lat, (int, float)) or not isinstance(lon, (int, float))
            or not -90 <= lat <= 90 or not -180 <= lon <= 180):
        raise ValueError('Invalid coordinates.')
    if type(radius) is not int or not 500 <= radius <= 5000:
        raise ValueError('Search radius must be between 500 and 5,000 meters.')
    if type(limit) is not int or not 1 <= limit <= 20:
        raise ValueError('Result limit must be between 1 and 20.')
    if cuisine is not None and (not isinstance(cuisine, str) or len(cuisine) > 100):
        raise ValueError('Cuisine must be under 100 characters.')
    key = (float(lat), float(lon), radius)
    global _next_request
    # Cache unfiltered searches so changing a cuisine doesn't repeat the API request.
    with _lock:
        cached = _cache.get(key)
        if cached and time.monotonic() - cached[0] < CACHE_SECONDS:
            places = cached[1]
            _cache.move_to_end(key)
        else:
            time.sleep(max(0, _next_request - time.monotonic()))
            _next_request = time.monotonic() + 2
            query = (f'[out:json][timeout:25];nwr["amenity"~"^(restaurant|cafe|fast_food|food_court)$"]'
                     f'(around:{radius},{float(lat)},{float(lon)});out center 300;')
            try:
                response = requests.post(URL, data={'data': query}, headers=HEADERS, timeout=35)
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, dict) or not isinstance(data.get('elements'), list) or data.get('remark'):
                    return None  # Don't present a timed-out partial response as complete.
                places = _parse(data, lat, lon)
            except (requests.RequestException, ValueError, TypeError, AttributeError):
                return None
            _cache[key] = (time.monotonic(), places)
            _cache.move_to_end(key)
            while len(_cache) > 128:
                _cache.popitem(last=False)
    term = _normalize(cuisine or '').strip()
    if term in {'vegetarian', 'vegan'}:
        places = [p for p in places if p.get(term) in {'yes', 'only'}]
    elif term:
        places = [p for p in places if term in _normalize(p['name'] + ' ' + p['detail'])]
    return copy.deepcopy(places[:limit])
