"""A real, isolated HTTP server for browser acceptance tests."""
from contextlib import contextmanager, ExitStack
from pathlib import Path
import sys
import threading


@contextmanager
def live_server(output):
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    from database_sandbox import DatabaseSandbox
    with ExitStack() as resources:
        sandbox = DatabaseSandbox()
        resources.callback(sandbox.close)
        from app import app
        from werkzeug.serving import make_server, WSGIRequestHandler

        class QuietHandler(WSGIRequestHandler):
            def log_request(self, *args, **kwargs):
                pass

        server = make_server('127.0.0.1', 0, app, threaded=True, request_handler=QuietHandler)
        # server_close must join active requests before the sandbox restores its
        # environment and removes SQLite files (Windows keeps open files locked).
        server.daemon_threads = False
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f'http://127.0.0.1:{server.server_port}'
        finally:
            server.shutdown()
            thread.join(timeout=10)
            server.server_close()
