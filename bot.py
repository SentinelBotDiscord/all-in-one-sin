import json
import os
import threading

_lock = threading.Lock()
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
os.makedirs(DATA_DIR, exist_ok=True)


def _path(name):
    return os.path.join(DATA_DIR, f"{name}.json")


def load(name, default=None):
    """Load a JSON data file by name (no extension). Returns default if missing."""
    if default is None:
        default = {}
    path = _path(name)
    with _lock:
        if not os.path.exists(path):
            with open(path, "w") as f:
                json.dump(default, f, indent=2)
            return json.loads(json.dumps(default))
        try:
            with open(path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError):
            return json.loads(json.dumps(default))


def save(name, data):
    """Save data to a JSON file by name (no extension)."""
    path = _path(name)
    with _lock:
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
