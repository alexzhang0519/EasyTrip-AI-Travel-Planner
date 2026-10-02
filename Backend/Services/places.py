"""Extract only real place coordinates returned by agent tools."""
import json
import math

def extract_pois(messages):
    places = {}
    centers = {}
    calls = {}
    for message in messages:
        for call in message.get('tool_calls', []):
            calls[call['id']] = call.get('function', {})
        if message.get('role') != 'tool':
            continue
        try:
            data = json.loads(message.get('content', 'null'))
        except (ValueError, TypeError):
            continue
        if isinstance(data, dict) and isinstance(data.get('name'), str) and 'lat' in data and 'lon' in data:
            centers[(data['lat'], data['lon'])] = data['name']
        if not isinstance(data, list):
            continue
        function = calls.get(message.get('tool_call_id'), {})
        try:
            args = json.loads(function.get('arguments', '{}'))
        except (ValueError, TypeError):
            args = {}
        location = centers.get((args.get('lat'), args.get('lon')))
        if not location and len(centers) == 1:
            location = next(iter(centers.values()))
        for place in data:
            if not isinstance(place, dict) or not place.get('name') or place.get('source') == 'yelp':
                continue
            lat, lon = place.get('lat'), place.get('lon')
            if not isinstance(lat, (float, int)) or not isinstance(lon, (float, int)):
                continue
            if not math.isfinite(lat) or not math.isfinite(lon) or not (-90 <= lat <= 90 and -180 <= lon <= 180):
                continue
            place = dict(place)
            if location:
                place['location'] = location
            places[(place['name'], lat, lon)] = place
    return list(places.values())
