"""Upgrade only exact, published defaults; never rewrite saved aircraft designs.

The historical records are public catalogue data from the cited Git commits.
Comparing the whole record protects any local edit, including unknown parameters.
"""
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / 'data' / 'projects'
COLUMNS = ('num', 'id', 'title', 'category', 'defaults', 'parameters', 'requirements')
JSON_COLUMNS = ('defaults', 'parameters', 'requirements')


def _decode(row):
    record = dict(row)
    for key in JSON_COLUMNS:
        record[key] = json.loads(record[key])
    return record


def refresh_unchanged_topics(connection, seed_path=ROOT / 'course_seed.json',
                             history_path=ROOT / 'topic_history.json'):
    """Atomically compare and replace recognized default topics in an open store.

    No write transaction is opened for current or locally edited records. The
    conditional UPDATE also protects an edit committed after the initial read.
    The caller supplies a schema-checked, autocommit SQLite connection.
    """
    seed = json.loads(Path(seed_path).read_text(encoding='utf8'))
    history = json.loads(Path(history_path).read_text(encoding='utf8'))
    if seed.get('schema') != 1 or history.get('schema') != 1:
        raise ValueError('Nieobsługiwana wersja katalogu początkowego lub jego historii.')
    latest = {topic['num']: topic for topic in seed['topics']}
    known = {}
    for item in history['known_defaults']:
        old = item['topic']
        if set(old) != set(COLUMNS) or not isinstance(old['num'], int):
            raise ValueError('Nieprawidłowy historyczny wpis katalogu tematów.')
        known.setdefault(old['num'], []).append(old)
    if not known:
        return []
    placeholders = ','.join('?' for _ in known)
    rows = connection.execute(f'SELECT * FROM topics WHERE num IN ({placeholders}) ORDER BY num', tuple(known)).fetchall()
    pending = []
    for row in rows:
        old = _decode(row)
        new = latest.get(old['num'])
        if new is not None and new != old and old in known[old['num']]:
            if set(new) != set(COLUMNS):
                raise ValueError('Nieprawidłowy aktualny wpis katalogu tematów.')
            pending.append((row, new))
    if not pending:
        return []
    assignments = ', '.join(f'{key} = ?' for key in COLUMNS if key != 'num')
    condition = ' AND '.join(f'{key} = ?' for key in COLUMNS)
    updated = []
    connection.execute('BEGIN IMMEDIATE')
    try:
        for old, new in pending:
            values = [json.dumps(new[key], ensure_ascii=False, sort_keys=True) if key in JSON_COLUMNS else new[key]
                      for key in COLUMNS if key != 'num']
            result = connection.execute(f'UPDATE topics SET {assignments} WHERE {condition}',
                                        (*values, *(old[key] for key in COLUMNS)))
            if result.rowcount:
                updated.append(new['num'])
        connection.execute('COMMIT')
    except BaseException:
        connection.execute('ROLLBACK')
        raise
    return updated
