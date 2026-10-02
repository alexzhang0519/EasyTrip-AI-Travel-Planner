"""Record sources from successful tool outputs, never from generated citations."""
import json
from urllib.parse import quote

def collect_sources(messages, places):
    sources = []
    if places:
        sources.append({'label': 'OpenStreetMap place listings', 'url': 'https://www.openstreetmap.org/copyright'})
    from Backend.app.services.evidence import weather_reports
    if any(w.get('daily') for w in weather_reports(messages)):
        sources.append({'label':'Weather: Open-Meteo (CC BY 4.0)','url':'https://open-meteo.com/'})
    calls = {}
    for message in messages:
        for call in message.get('tool_calls', []):
            calls[call['id']] = call.get('function', {})
        function = calls.get(message.get('tool_call_id'), {})
        if message.get('role') != 'tool' or function.get('name') != 'lookup_travel_info':
            continue
        try:
            result = json.loads(message.get('content', 'null'))
            city = json.loads(function.get('arguments', '{}')).get('city')
        except (ValueError, TypeError):
            continue
        if isinstance(result, str) and result and not result.startswith('No travel guide found') and isinstance(city, str):
            sources.append({'label': f'Wikivoyage: {city}', 'url': 'https://en.wikivoyage.org/wiki/' + quote(city.replace(' ', '_'), safe='')})
    return list({s['url']: s for s in sources}.values())
