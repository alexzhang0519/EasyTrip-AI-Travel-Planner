from flask import jsonify
from . import api
from .common import payload, text_field
from Backend.app.services.geocoding import geocode_city
from Backend.app.services.restaurants import search_restaurants

@api.post('/restaurants')
def restaurants():
    data = payload()
    city = text_field(data, 'city', 150)
    cuisine = data.get('cuisine', '')
    radius = data.get('radius', 1500)
    if not isinstance(cuisine, str) or len(cuisine) > 100:
        raise ValueError('Cuisine must be under 100 characters.')
    if type(radius) is not int or radius not in (1000, 1500, 3000, 5000):
        raise ValueError('Choose a supported search radius.')
    location = geocode_city(city)
    if location is None:
        return jsonify(error='City lookup failed. Try a more specific city and country.'), 502
    results = search_restaurants(location['lat'], location['lon'], radius=radius, cuisine=cuisine or None, limit=10)
    if results is None:
        return jsonify(error='The free map service is temporarily unavailable. Try again later; no paid fallback is used.'), 502
    results = [dict(p, location=location.get('name') or city) for p in results]
    return jsonify(restaurants=results)
