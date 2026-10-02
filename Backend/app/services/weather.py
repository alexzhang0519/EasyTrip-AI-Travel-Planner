"""Cached Open-Meteo forecasts; free personal/non-commercial endpoint, no key.
Provider terms: https://open-meteo.com/en/pricing
"""
from collections import OrderedDict
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import math
import threading
import time
from zoneinfo import ZoneInfo
import requests

FORECAST_URL = 'https://api.open-meteo.com/v1/forecast'
FORECAST_DAYS = 16
CACHE_TTL = 900
CACHE_LIMIT = 128
_cache = OrderedDict()
_lock = threading.Lock()
_FIELDS = ('temperature_2m_min', 'temperature_2m_max', 'precipitation_probability_max', 'weather_code')


def _now():
    return datetime.now(timezone.utc)


def _validate(lat, lon, start_date, days):
    for value, bound in ((lat, 90), (lon, 180)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or abs(value) > bound:
            raise ValueError('Latitude and longitude must be finite numbers within geographic bounds.')
    if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= 30:
        raise ValueError('Weather trip length must be an integer from 1 to 30 days.')
    if start_date is not None:
        if not isinstance(start_date, str):
            raise ValueError('Start date must use YYYY-MM-DD.')
        try:
            parsed = date.fromisoformat(start_date)
            if parsed.isoformat() != start_date:
                raise ValueError()
        except ValueError as exc:
            raise ValueError('Start date must use YYYY-MM-DD.') from exc


def _forecast(lat, lon):
    key = (lat, lon)
    with _lock:
        cached = _cache.get(key)
        if cached and time.monotonic() - cached[0] < CACHE_TTL:
            payload, fetched = cached[1:]
            if _now().astimezone(ZoneInfo(payload['timezone'])).date().isoformat() == payload['daily']['time'][0]:
                _cache.move_to_end(key)
                return deepcopy(payload), fetched
    response = requests.get(FORECAST_URL, params={
        'latitude': lat, 'longitude': lon, 'timezone': 'auto',
        'forecast_days': FORECAST_DAYS, 'daily': ','.join(_FIELDS),
        'temperature_unit': 'celsius',
    }, timeout=12)
    response.raise_for_status()
    payload = response.json()
    fetched = _now().isoformat()
    ZoneInfo(payload['timezone'])
    dates = payload['daily']['time']
    if not isinstance(dates, list) or not dates:
        raise ValueError('Missing daily dates')
    for field in _FIELDS:
        if not isinstance(payload['daily'].get(field), list) or len(payload['daily'][field]) != len(dates):
            raise ValueError('Incomplete daily arrays')
    for day in dates:
        date.fromisoformat(day)
    with _lock:
        _cache[key] = (time.monotonic(), deepcopy(payload), fetched)
        _cache.move_to_end(key)
        while len(_cache) > CACHE_LIMIT:
            _cache.popitem(last=False)
    return payload, fetched


def get_weather(lat: float, lon: float, start_date: str | None = None, days: int = 3):
    """Return actual forecast overlap, with destination-local dates.

    Invalid input raises ValueError. Upstream failures return unavailable.
    No historical or climate data is substituted for missing forecasts.
    """
    _validate(lat, lon, start_date, days)
    result = dict(status='unavailable', source='Open-Meteo', outlook_only=start_date is None,
                  source_url='https://open-meteo.com/', timezone=None,
                  fetched_at=None, requested_start_date=start_date, requested_days=days,
                  forecast_start_date=None, forecast_end_date=None,
                  forecast_horizon_days=FORECAST_DAYS, daily=[], warnings=[])
    try:
        payload, fetched = _forecast(lat, lon)
        today = _now().astimezone(ZoneInfo(payload['timezone'])).date()
        last = today + timedelta(days=FORECAST_DAYS - 1)
        start = date.fromisoformat(start_date) if start_date else today
        end = start + timedelta(days=days - 1)
        result.update(timezone=payload['timezone'], fetched_at=fetched,
                      requested_start_date=start.isoformat(),
                      forecast_start_date=today.isoformat(), forecast_end_date=last.isoformat())
        if end < today or start > last:
            result.update(status='out_of_range', warnings=[
                f'No forecast is available for this trip. The forecast horizon is {today} through {last} (up to 16 days).'])
            return result
        daily = payload['daily']
        seen = set()
        for index, day_text in enumerate(daily['time']):
            day = date.fromisoformat(day_text)
            if day in seen or not max(today, start) <= day <= min(last, end):
                continue
            values = [daily[field][index] for field in _FIELDS]
            if any(isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v) for v in values):
                continue
            low, high, rain, code = values
            if low > high or not 0 <= rain <= 100 or int(code) != code or not 0 <= code <= 99:
                continue
            seen.add(day)
            result['daily'].append(dict(date=day.isoformat(), temperature_min_c=low,
                temperature_max_c=high, precipitation_probability_max=rain, weather_code=int(code)))
        result['daily'].sort(key=lambda row: row['date'])
        count = len(result['daily'])
        result['status'] = 'available' if count == days else ('partial' if count else 'unavailable')
        if count != days:
            result['warnings'].append(f'Forecast covers {count} of {days} requested days. Missing days have no verified forecast; the maximum horizon is 16 days.')
        return result
    except (requests.RequestException, ValueError, KeyError, TypeError, IndexError, OverflowError):
        result['warnings'] = ['Weather is temporarily unavailable. Do not infer weather conditions; try again later.']
        return result
