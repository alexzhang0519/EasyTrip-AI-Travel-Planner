from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from unittest.mock import Mock

import pytest
import requests
from Backend.app.services import weather


@pytest.fixture(autouse=True)
def isolated_cache(monkeypatch):
    weather._cache.clear()
    monkeypatch.setattr(weather, '_now', lambda: datetime(2026, 10, 2, 1, tzinfo=timezone.utc))
    yield
    weather._cache.clear()


@pytest.fixture
def forecast(monkeypatch):
    # UTC October 2 is still October 1 in New York.
    data = {'timezone': 'America/New_York', 'daily': {
        'time': [(date(2026, 10, 1) + timedelta(days=i)).isoformat() for i in range(16)],
        'temperature_2m_min': [10] * 16, 'temperature_2m_max': [20] * 16,
        'precipitation_probability_max': [25] * 16, 'weather_code': [3] * 16}}
    response = Mock()
    response.json.side_effect = lambda: deepcopy(data)
    get = Mock(return_value=response)
    monkeypatch.setattr(weather.requests, 'get', get)
    return data, get


def test_local_today_and_provider_parameters(forecast):
    _, get = forecast
    result = weather.get_weather(40.7, -74)
    assert result['status'] == 'available'
    assert result['requested_start_date'] == '2026-10-01'
    assert result['forecast_end_date'] == '2026-10-16'
    assert len(result['daily']) == 3
    assert result['daily'][0] == {'date': '2026-10-01', 'temperature_min_c': 10,
        'temperature_max_c': 20, 'precipitation_probability_max': 25, 'weather_code': 3}
    assert result['fetched_at']
    params = get.call_args.kwargs['params']
    assert params['forecast_days'] == 16 and params['timezone'] == 'auto'
    assert 'apikey' not in params


@pytest.mark.parametrize('start,days,count', [('2026-10-15', 5, 2), ('2026-09-30', 3, 2), ('2026-10-01', 30, 16)])
def test_partial_horizon(forecast, start, days, count):
    result = weather.get_weather(40, -74, start, days)
    assert result['status'] == 'partial'
    assert len(result['daily']) == count
    assert result['warnings']


@pytest.mark.parametrize('start', ['2026-09-01', '2026-10-17', '2027-01-01'])
def test_outside_horizon(forecast, start):
    result = weather.get_weather(40, -74, start)
    assert result['status'] == 'out_of_range' and result['daily'] == []


@pytest.mark.parametrize('args', [(91, 0), (0, -181), (float('nan'), 0), (True, 0),
    (0, 0, '2026-02-30'), (0, 0, '20261002'), (0, 0, None, 31), (0, 0, None, True), (0, 0, None, 0)])
def test_invalid_input_does_not_call_provider(forecast, args):
    with pytest.raises(ValueError):
        weather.get_weather(*args)
    forecast[1].assert_not_called()


def test_upstream_failure(forecast):
    forecast[1].side_effect = requests.Timeout()
    result = weather.get_weather(40, -74)
    assert result['status'] == 'unavailable' and result['daily'] == []
    assert result['warnings']


@pytest.mark.parametrize('change', ['null', 'malformed', 'invalid_zone', 'invalid_value'])
def test_missing_or_malformed_data(forecast, change):
    data, _ = forecast
    if change == 'null':
        data['daily']['temperature_2m_min'][0] = None
    elif change == 'malformed':
        data['daily']['time'] = []
    elif change == 'invalid_zone':
        data['timezone'] = 'not/a/zone'
    else:
        data['daily']['precipitation_probability_max'][0] = 101
    result = weather.get_weather(40, -74)
    assert result['status'] == ('partial' if change in ('null', 'invalid_value') else 'unavailable')
    assert result['warnings']


def test_cache_reused_immutable_and_bounded(forecast, monkeypatch):
    monkeypatch.setattr(weather, 'CACHE_LIMIT', 2)
    first = weather.get_weather(40, -74)
    first['daily'][0]['temperature_min_c'] = 999
    assert weather.get_weather(40, -74)['daily'][0]['temperature_min_c'] == 10
    assert forecast[1].call_count == 1
    weather.get_weather(41, -74)
    weather.get_weather(42, -74)
    assert len(weather._cache) == 2


def test_cache_expires(forecast, monkeypatch):
    monkeypatch.setattr(weather.time, 'monotonic', lambda: 0)
    weather.get_weather(40, -74)
    monkeypatch.setattr(weather.time, 'monotonic', lambda: weather.CACHE_TTL + 1)
    weather.get_weather(40, -74)
    assert forecast[1].call_count == 2


def test_destination_midnight_refreshes_cache(forecast, monkeypatch):
    weather.get_weather(40, -74)
    monkeypatch.setattr(weather, '_now', lambda: datetime(2026, 10, 2, 5, tzinfo=timezone.utc))
    weather.get_weather(40, -74)
    assert forecast[1].call_count == 2
