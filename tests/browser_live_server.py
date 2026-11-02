"""A real, isolated HTTP server for browser acceptance tests."""
from contextlib import contextmanager
import os
from pathlib import Path
import shutil
import sys
import threading


@contextmanager
def live_server(output):
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    database = output / 'aircraft.sqlite3'
    shutil.copyfile(root / 'data/aircraft/aircraft.sqlite3', database)
    previous = os.environ.get('BIPOL_AIRCRAFT_DB')
    os.environ['BIPOL_AIRCRAFT_DB'] = str(database)
    from app import app
    from werkzeug.serving import make_server, WSGIRequestHandler

    class QuietHandler(WSGIRequestHandler):
        def log_request(self, *args, **kwargs):
            pass

    server = make_server('127.0.0.1', 0, app, threaded=True, request_handler=QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}'
    finally:
        server.shutdown()
        thread.join(timeout=10)
        server.server_close()
        if previous is None:
            os.environ.pop('BIPOL_AIRCRAFT_DB', None)
        else:
            os.environ['BIPOL_AIRCRAFT_DB'] = previous
