"""Validate model output and build map URLs independently of generated prose."""
from urllib.parse import urlencode
from Backend.app.models.schemas import PlannerResponse

def map_url(place):
    query = ', '.join(p.strip() for p in (place.name, place.address or '', place.city) if p.strip())
    return 'https://www.google.com/maps/search/?' + urlencode({'api': '1', 'query': query})

def normalize_plan(content):
    parsed = PlannerResponse.model_validate_json(content)
    if len(parsed.days) > 30 or any(not 1 <= day.day <= 30 or len(day.activities) > 20 for day in parsed.days):
        raise ValueError('Itinerary exceeds supported size')
    if len({d.day for d in parsed.days}) != len(parsed.days):
        raise ValueError('Duplicate itinerary day')
    result = parsed.model_dump()
    lines = [parsed.summary]
    for day, output in zip(parsed.days, result['days']):
        lines.append(f'\nDay {day.day}: {day.title}')
        for activity, data in zip(day.activities, output['activities']):
            label = ''
            if activity.place:
                if not activity.place.name.strip() or not activity.place.city.strip():
                    raise ValueError('Places require a name and city')
                data['place']['map_url'] = map_url(activity.place)
                label = f"[{activity.place.name}]({data['place']['map_url']}) — "
            lines.append(f'{activity.period}: {label}{activity.description}')
    lines.extend(parsed.warnings)
    return '\n'.join(lines), result
