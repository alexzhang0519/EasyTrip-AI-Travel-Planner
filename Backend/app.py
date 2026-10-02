"""Application factory: serve the frontend and register JSON API routes."""
import os
import secrets
from pathlib import Path
from flask import Flask, jsonify, request
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / 'Backend' / '.env')

def create_app(test_config=None):
    app = Flask(__name__, template_folder=str(ROOT / 'Frontend/templates'),
                static_folder=str(ROOT / 'Frontend/static'), static_url_path='/static')
    app.config.update(SECRET_KEY=os.getenv('FLASK_SECRET_KEY') or secrets.token_hex(32),
                      MAX_CONTENT_LENGTH=32 * 1024, SESSION_COOKIE_HTTPONLY=True,
                      SESSION_COOKIE_SAMESITE='Strict', STORAGE_DIR=ROOT / 'Backend/storage')
    if test_config:
        app.config.update(test_config)
    from Backend.routes.pages import pages
    from Backend.routes.api import api
    app.register_blueprint(pages)
    app.register_blueprint(api)

    @app.before_request
    def protect_writes():
        if request.path.startswith('/api/') and request.method == 'POST':
            if request.headers.get('X-EasyTrip') != '1':
                return jsonify(error='Please submit this request through EasyTrip.'), 403
            origin = request.headers.get('Origin')
            if origin and origin != request.host_url.rstrip('/'):
                return jsonify(error='Cross-site requests are not allowed.'), 403

    @app.errorhandler(413)
    def too_large(error):
        return jsonify(error='This request is too large. Please shorten your message.'), 413

    @app.errorhandler(500)
    def failed(error):
        if request.path.startswith('/api/'):
            return jsonify(error='Something went wrong. Please retry.'), 500
        return 'Something went wrong. Please retry.', 500
    return app
