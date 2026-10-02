"""Compatibility for existing imports; routes now have separate modules."""
import sys
from Backend.app.api.routes import chat
sys.modules[__name__] = chat
