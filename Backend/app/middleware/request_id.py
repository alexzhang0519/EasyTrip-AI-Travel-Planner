import uuid
from flask import g

def register(app):
    @app.before_request
    def assign_request_id():
        g.request_id = uuid.uuid4().hex

    @app.after_request
    def attach_request_id(response):
        if not hasattr(g, 'request_id'):
            g.request_id = uuid.uuid4().hex
        response.headers['X-Request-ID'] = g.request_id
        if response.is_json and response.status_code >= 400:
            data = response.get_json(silent=True)
            if isinstance(data, dict):
                data['request_id'] = g.request_id
                response.set_data(app.json.dumps(data))
        return response
