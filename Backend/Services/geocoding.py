"""Explicit city searches with bounded caching and a shared one-request/second limit."""
from collections import OrderedDict
import threading
import time
import requests

HEADERS = {'User-Agent': 'EasyTrip/1.0 (personal local travel planner)'}
SEARCH_URL = 'https://nominatim.openstreetmap.org/search'
MIN_INTERVAL = 1.0
_lock = threading.Lock()
_next_request = 0.0
_cache = OrderedDict()


def geocode_city(city: str, max_retries: int = 3):
    if not isinstance(city, str) or not city.strip():
        return None
    city = city.strip()
    key = city.casefold()
    global _next_request
    with _lock:
        cached = _cache.get(key)
        if cached and time.monotonic() - cached[0] < 86400:
            _cache.move_to_end(key)
            return dict(cached[1]) if cached[1] else None
        for attempt in range(max_retries):
            time.sleep(max(0, _next_request - time.monotonic()))
            _next_request = time.monotonic() + MIN_INTERVAL
            try:
                response = requests.get(SEARCH_URL, params={'q': city, 'format': 'json', 'limit': 1},
                                        headers=HEADERS, timeout=10)
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, list):
                    return None
                result = None if not data else {'name': data[0]['display_name'],
                    'lat': float(data[0]['lat']), 'lon': float(data[0]['lon'])}
                _cache[key] = (time.monotonic(), result)
                _cache.move_to_end(key)
                while len(_cache) > 128:
                    _cache.popitem(last=False)
                return dict(result) if result else None
            except requests.RequestException:
                if attempt + 1 < max_retries:
                    time.sleep(2 ** attempt)
            except (ValueError, KeyError, TypeError):
                return None
    return None
