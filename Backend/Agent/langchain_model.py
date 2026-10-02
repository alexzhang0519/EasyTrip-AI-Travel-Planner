"""Compatibility import; implementation lives in Backend.app.agents.langchain_model."""
import sys
from importlib import import_module
sys.modules[__name__] = import_module("Backend.app.agents.langchain_model")
