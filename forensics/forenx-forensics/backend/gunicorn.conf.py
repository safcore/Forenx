"""Gunicorn process configuration for ForenX production.

Do not use `manage.py runserver` in production. Terminate TLS at a reverse
proxy and bind Gunicorn to a local interface.
"""

from __future__ import annotations

import os
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
repo_root = backend_dir.parent

wsgi_app = "config.wsgi:application"
chdir = str(backend_dir)
bind = os.environ.get("GUNICORN_BIND", "127.0.0.1:8000")
workers = int(os.environ.get("GUNICORN_WORKERS", "3"))
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "120"))
graceful_timeout = 30
keepalive = 5
worker_class = "sync"
max_requests = 1000
max_requests_jitter = 50
accesslog = "-"
errorlog = "-"
capture_output = True
raw_env = [
    f"PYTHONPATH={backend_dir}{os.pathsep}{repo_root}",
]
