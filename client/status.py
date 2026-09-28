import collections
import sys
import threading
import time

import config

_lock = threading.Lock()
_history = collections.deque(maxlen=config.PANEL_HISTORY)
_logs = collections.deque(maxlen=config.PANEL_LOG_LINES)


class _Tee:
    """passes output through to the journal and keeps the last lines for the panel"""

    def __init__(self, stream):
        self.stream = stream
        self.partial = ""

    def write(self, s):
        self.stream.write(s)
        with _lock:
            *lines, self.partial = (self.partial + s).split("\n")
            _logs.extend((time.time(), line) for line in lines)
        return len(s)

    def __getattr__(self, name):
        return getattr(self.stream, name)


def capture_output():
    sys.stdout = _Tee(sys.stdout)
    sys.stderr = _Tee(sys.stderr)


def add_conversation(entry):
    with _lock:
        _history.append(entry)


def snapshot():
    with _lock:
        return {
            "history": list(_history),
            "logs": [{"time": t, "line": line} for t, line in _logs],
        }
