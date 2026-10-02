"""Compatibility import; implementation lives in Backend.app.services.rag."""
import sys
from importlib import import_module
sys.modules[__name__] = import_module("Backend.app.services.rag")
