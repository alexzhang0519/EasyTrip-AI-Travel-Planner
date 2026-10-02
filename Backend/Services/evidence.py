"""Compatibility import; implementation lives in Backend.app.services.evidence."""
import sys
from importlib import import_module
sys.modules[__name__] = import_module("Backend.app.services.evidence")
