from pathlib import Path
from flask import jsonify
from . import api
from .common import planning_lock, payload, text_field, trip_path, visible
from Backend.app.memory import trips as persistence, conversations

@api.get('/trips')
def trips():
    return jsonify(trips=[{'id': Path(t['path']).name, 'name': t['name'], 'saved_at': t['saved_at']}
                          for t in persistence.list_trips()])

@api.post('/trips')
def save():
    name = text_field(payload(), 'name', 100)
    with planning_lock:
        data = conversations.read()
        if not any(m['role'] == 'assistant' for m in data['messages']):
            raise ValueError('Plan a trip before saving it.')
        path = persistence.save_trip(name, data['messages'], data['pois'])
    return jsonify(id=Path(path).name, name=name), 201

@api.post('/trips/<trip_id>/load')
def load(trip_id):
    with planning_lock:
        data = persistence.load_trip(trip_path(trip_id))
        conversations.write({'messages': data['messages'], 'pois': data.get('pois', [])})
    return jsonify(visible(data))

@api.post('/trips/<trip_id>/feedback')
def feedback(trip_id):
    data = payload()
    if data.get('rating') not in ('up', 'down'):
        raise ValueError('Choose a valid feedback rating.')
    comment = data.get('comment', '')
    if not isinstance(comment, str) or len(comment) > 1000:
        raise ValueError('Feedback must be under 1,000 characters.')
    persistence.save_feedback(trip_path(trip_id), data['rating'], comment.strip())
    return jsonify(ok=True)



@api.post('/trips/plan')
def direct_plan():
    from Backend.app.models.schemas import TripRequest
    from .chat import plan_message
    data = TripRequest.model_validate(payload())
    if not data.destination.strip(): raise ValueError('Destination cannot be blank.')
    message = (f'Plan a {data.days}-day trip to {data.destination}. Start date: {data.start_date or "not set; current weather outlook only"}. '
               f'Pace: {data.pace}. Getting around: {data.transport}. Interests: {data.interests}. Budget and preferences: {data.preferences}. '
               f'Food preferences and dietary needs: {data.food_preferences}. Include lunch and dinner near the sightseeing stops in each full day.')
    return plan_message(message, data.collaborate, fresh=True)


@api.post('/trips/<trip_id>/delete')
def delete(trip_id):
    with planning_lock:
        persistence.delete_trip(trip_path(trip_id))
    return jsonify(ok=True)
