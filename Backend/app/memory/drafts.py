"""Temporary browser-page drafts, never persisted to disk."""
from copy import deepcopy
from threading import RLock, Timer
from time import monotonic

class DraftStore:
    def __init__(self, ttl=1800):
        self.ttl = ttl
        self.entries = {}
        self.lock = RLock()
        self.timer = None

    def _sweep(self):
        now = monotonic()
        self.entries = {k: v for k, v in self.entries.items() if v[0] > now}

    def _schedule(self):
        if self.timer is None and self.entries:
            self.timer = Timer(60, self._tick)
            self.timer.daemon = True
            self.timer.start()

    def _tick(self):
        with self.lock:
            self.timer = None
            self._sweep()
            self._schedule()

    def start(self, key):
        with self.lock:
            self._sweep()
            if key not in self.entries:
                if len(self.entries) >= 256:
                    raise ValueError('Too many open drafts. Close unused planner tabs and retry.')
                self.entries[key] = (monotonic() + self.ttl, {'messages': [], 'pois': []})
                self._schedule()
            return self.read(key)

    def read(self, key):
        with self.lock:
            self._sweep()
            entry = self.entries.get(key)
            if entry is None or entry[1] is None:
                raise ValueError('This draft has closed or expired. Reload the planner to start again.')
            self.entries[key] = (monotonic() + self.ttl, entry[1])
            return deepcopy(entry[1])

    def write(self, key, data):
        with self.lock:
            self.read(key)  # A late model response cannot revive a closed draft.
            self.entries[key] = (monotonic() + self.ttl, deepcopy(data))

    def close(self, key):
        with self.lock:
            if key in self.entries:
                self.entries[key] = (monotonic() + self.ttl, None)
