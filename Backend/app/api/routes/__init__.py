from flask import Blueprint
api = Blueprint('api', __name__, url_prefix='/api')
from . import chat, trip, map  # register domain routes
