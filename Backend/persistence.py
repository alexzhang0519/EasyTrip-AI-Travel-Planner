"""Compatibility import; implementation lives in Backend.app.memory.trips."""
import sys
from importlib import import_module
sys.modules[__name__] = import_module("Backend.app.memory.trips")
