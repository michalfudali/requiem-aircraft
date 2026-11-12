"""Isolate both SQLite stores before importing any application module.

Standard library only: importing calculations already reads the course database.
Each pytest worker and browser server owns a separate pair of database files.
"""
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import tempfile

ROOT = Path(__file__).resolve().parents[1]
STORES = {
    'BIPOL_AIRCRAFT_DB': ROOT / 'data/aircraft/aircraft.sqlite3',
    'BIPOL_PROJECTS_DB': ROOT / 'data/projects/projects.sqlite3',
}


def backup(source, destination):
    with closing(sqlite3.connect(f'{Path(source).resolve().as_uri()}?mode=ro', uri=True)) as src:
        with closing(sqlite3.connect(destination, timeout=30)) as dst:
            src.backup(dst)


class DatabaseSandbox:
    def __init__(self):
        self.directory = tempfile.TemporaryDirectory(prefix='bipol-tests-')
        self.previous = {key: os.environ.get(key) for key in STORES}
        self.paths = {}
        self.pristine = {}
        for key, source in STORES.items():
            if key == 'BIPOL_PROJECTS_DB' and not source.is_file():
                from production import initialize_projects
                initialize_projects(source)
            self.paths[key] = Path(self.directory.name) / source.name
            self.pristine[key] = Path(self.directory.name) / ('pristine-' + source.name)
            backup(source, self.pristine[key])
            backup(self.pristine[key], self.paths[key])
        # Publish paths only after both snapshots have been created successfully.
        for key in STORES:
            os.environ[key] = str(self.paths[key])

    def restore(self, key):
        backup(self.pristine[key], self.paths[key])

    def capture_pristine(self):
        """Freeze the initialized application state, including safe catalogue upgrades."""
        for key in STORES:
            backup(self.paths[key], self.pristine[key])

    def close(self):
        for key, value in self.previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.directory.cleanup()
