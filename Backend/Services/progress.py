"""Request-local progress callback and bounded, session-scoped status storage."""
from contextvars import ContextVar
from collections import OrderedDict
from threading import Lock
from time import monotonic

callback = ContextVar('planning_progress', default=None)
_entries = OrderedDict()
_lock = Lock()

def report(stage):
    listener = callback.get()
    if listener:
        listener(stage)

def update(key, stage):
    with _lock:
        _entries[key] = (monotonic(), stage)
        _entries.move_to_end(key)
        while len(_entries) > 256:
            _entries.popitem(last=False)

def read(key):
    with _lock:
        stamp, stage = _entries.get(key, (0, 'idle'))
        return stage if monotonic() - stamp < 900 else 'idle'
