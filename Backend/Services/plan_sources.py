"""Compatibility import; implementation lives in Backend.app.services.plan_sources."""
import sys
from importlib import import_module
sys.modules[__name__] = import_module("Backend.app.services.plan_sources")
