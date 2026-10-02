"""Compatibility import; implementation lives in Backend.app.api.routes.pages."""
import sys
from importlib import import_module
sys.modules[__name__] = import_module("Backend.app.api.routes.pages")
