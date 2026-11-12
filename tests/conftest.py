"""Worker-local databases, automatic rollback and opt-in browser acceptance tests."""
import atexit
from contextlib import ExitStack, closing
from copy import deepcopy
import sqlite3

import pytest

pytest_plugins = ['browser_fixtures']

from database_sandbox import DatabaseSandbox

# This must precede *all* calculations/app imports, including in xdist workers.
SANDBOX = DatabaseSandbox()
atexit.register(SANDBOX.close)

from app import app  # noqa: E402
from calculations.trends import load_aircraft  # noqa: E402
from calculations.engine_fuel import _catalog  # noqa: E402

SANDBOX.capture_pristine()


def pytest_addoption(parser):
    parser.addoption('--browser', action='store_true', help='Include real Chromium acceptance tests')


def pytest_collection_modifyitems(config, items):
    if not config.getoption('--browser'):
        selected = [item for item in items if 'browser' not in item.keywords]
        deselected = [item for item in items if 'browser' in item.keywords]
        items[:] = selected
        config.hook.pytest_deselected(items=deselected)


@pytest.fixture(autouse=True)
def restore_shared_state():
    """Restore modified stores even if a test forgot isolated_db or failed.

    A retained connection sees commits by other connections and subprocesses,
    including WAL. Read-only tests need no database copy.
    """
    config = deepcopy(dict(app.config))
    with ExitStack() as stack:
        monitors = {key: stack.enter_context(closing(sqlite3.connect(path)))
                    for key, path in SANDBOX.paths.items()}
        versions = {key: con.execute('PRAGMA data_version').fetchone()[0] for key, con in monitors.items()}
        try:
            yield
        finally:
            changed = [key for key, con in monitors.items()
                       if con.execute('PRAGMA data_version').fetchone()[0] != versions[key]]
            stack.close()
            for key in changed:
                SANDBOX.restore(key)
            load_aircraft.cache_clear()
            _catalog.cache_clear()
            app.config.clear()
            app.config.update(config)


@pytest.fixture
def client():
    """Provides a Flask test client configured in TESTING mode."""
    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client


@pytest.fixture
def isolated_db():
    """Compatibility fixture; isolation now applies to every test and both stores."""
    yield
