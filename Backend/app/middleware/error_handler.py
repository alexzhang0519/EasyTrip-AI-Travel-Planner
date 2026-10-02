from flask import jsonify, request
from pydantic import ValidationError

def register(app):
    @app.errorhandler(ValidationError)
    def invalid_schema(error):
        fields = ', '.join('.'.join(map(str,e['loc'])) for e in error.errors(include_input=False))
        return jsonify(error=f'Invalid request fields: {fields}.'), 400

    @app.errorhandler(ValueError)
    def invalid(error):
        return jsonify(error=str(error)), 400

    @app.errorhandler(FileNotFoundError)
    def missing(error):
        return jsonify(error='Saved trip not found.'), 404

    @app.errorhandler(413)
    def too_large(error):
        return jsonify(error='This request is too large. Please shorten your message.'), 413

    @app.errorhandler(500)
    def failed(error):
        if request.path.startswith('/api/'):
            return jsonify(error='Something went wrong. Please retry.'), 500
        return 'Something went wrong. Please retry.', 500
