"""Read-only, loopback-only learning roadmap. No vault writes or model calls."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sqlite3
import threading
import time
from datetime import date, datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

BASE = Path(__file__).resolve().parent
MAX_FILES = 2000
MAX_BYTES = 1024 * 1024
SCAN_SECONDS = 4
TOPICS = {
    1: ('memory-hierarchy-and-access-latency', 'memory-hierarchy-sram-dram-tradeoffs',
        'cpu-virtualization-and-time-sharing', 'process-abstraction-and-machine-state',
        'process-lifecycle-and-os-apis', 'process-state-transitions'),
    7: ('attention-mechanisms-in-transformer-architecture', 'mixture-of-experts',
        'kv-caching-and-memory-considerations-in-transformers', 'cpu-vs-gpu-for-ml'),
    8: ('inference-engineering-systems-and-performance', 'llm-inference-serving-systems',
        'training-vs-inference-systems-optimization'),
    9: ('eval-frameworks', 'agent-evaluation-methods-evals',
        'reflection-and-external-feedback-in-agentic-ai',
        'design-patterns-for-llm-agents-reflection-and-multi-agent-systems'),
}
LAYER_BY_SLUG = {slug: layer for layer, slugs in TOPICS.items() for slug in slugs}
DECISIONS = {'review', 'continue', 'skip_reading_and_prove', 'start_new'}
DECISION_LABELS = {
    'review': 'Review old notes first',
    'continue': 'Continue the course',
    'skip_reading_and_prove': 'Skip reading and prove it',
    'start_new': 'Start new material',
}


class StaleWrite(Exception):
    """A progress write was based on a version that is no longer current."""


class AppStore:
    """Durable app-owned state. It never stores Markdown bodies or writes the vault."""
    def __init__(self, path=BASE / 'data' / 'learning-app.sqlite3'):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path, self.lock = path, threading.Lock()
        with self.connect() as db:
            db.executescript('''
              CREATE TABLE IF NOT EXISTS app_state (id INTEGER PRIMARY KEY CHECK(id=1), progress_json TEXT NOT NULL, quiz_json TEXT NOT NULL, updated_at TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS learning_decision (task_id TEXT PRIMARY KEY, decision TEXT NOT NULL, note_ids_json TEXT NOT NULL, rationale TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS coverage_snapshot (note_id TEXT PRIMARY KEY, title TEXT NOT NULL, entry_date TEXT, content_hash TEXT NOT NULL, layer_id INTEGER, concepts_json TEXT NOT NULL, matched_at TEXT NOT NULL);
            ''')
            columns = [row[1] for row in db.execute('PRAGMA table_info(app_state)')]
            if 'evidence_json' not in columns:
                db.execute("ALTER TABLE app_state ADD COLUMN evidence_json TEXT NOT NULL DEFAULT '{}'")
    def connect(self):
        return sqlite3.connect(self.path)

    def progress(self):
        with self.connect() as db:
            row = db.execute('SELECT progress_json, quiz_json, evidence_json, updated_at FROM app_state WHERE id=1').fetchone()
        return {'checkpoints': json.loads(row[0]), 'quiz_attempts': json.loads(row[1]), 'evidence_notes': json.loads(row[2]), 'updated_at': row[3]} if row else {'checkpoints': None, 'quiz_attempts': {}, 'evidence_notes': {}, 'updated_at': None}

    def save_progress(self, body):
        checkpoints, quizzes, evidence_notes = body.get('checkpoints'), body.get('quiz_attempts', {}), body.get('evidence_notes', {})
        if not isinstance(checkpoints, list) or len(checkpoints) != 36 or not all(isinstance(x, dict) and isinstance(x.get('done'), bool) for x in checkpoints) or not isinstance(quizzes, dict):
            raise ValueError('Invalid app progress')
        if not isinstance(evidence_notes, dict) or not all(isinstance(key, str) and re.fullmatch(r'layer-[1-9]-(task-[0-3]|proof)', key) and isinstance(value, str) and len(value) <= 5000 for key, value in evidence_notes.items()):
            raise ValueError('Invalid evidence notes')
        base = body.get('base_updated_at')
        if base is not None and not isinstance(base, str):
            raise ValueError('Invalid app progress')
        with self.lock, self.connect() as db:
            row = db.execute('SELECT updated_at FROM app_state WHERE id=1').fetchone()
            if base is not None and row and row[0] != base:
                raise StaleWrite()  # Another device saved since this client last read.
            stamp = datetime.now(timezone.utc).isoformat(timespec='microseconds')  # Version token: must differ per write.
            db.execute('INSERT INTO app_state(id,progress_json,quiz_json,evidence_json,updated_at) VALUES(1,?,?,?,?) ON CONFLICT(id) DO UPDATE SET progress_json=excluded.progress_json,quiz_json=excluded.quiz_json,evidence_json=excluded.evidence_json,updated_at=excluded.updated_at', (json.dumps(checkpoints), json.dumps(quizzes), json.dumps(evidence_notes), stamp))
        return self.progress()

    def decisions(self):
        with self.connect() as db:
            rows = db.execute('SELECT task_id,decision,note_ids_json,rationale,created_at,updated_at FROM learning_decision').fetchall()
        return {r[0]: {'decision':r[1], 'note_ids':json.loads(r[2]), 'rationale':r[3], 'created_at':r[4], 'updated_at':r[5]} for r in rows}

    def save_decision(self, body):
        task_id, decision = body.get('task_id'), body.get('decision')
        if not isinstance(task_id, str) or not re.fullmatch(r'layer-[1-9]', task_id) or decision not in DECISIONS: raise ValueError('Invalid decision')
        note_ids = body.get('note_ids', [])
        if not isinstance(note_ids, list) or not all(isinstance(x, str) and x.startswith('_wiki/cs/') for x in note_ids): raise ValueError('Invalid note identifiers')
        stamp = now()
        with self.lock, self.connect() as db:
            db.execute('INSERT INTO learning_decision(task_id,decision,note_ids_json,rationale,created_at,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT(task_id) DO UPDATE SET decision=excluded.decision,note_ids_json=excluded.note_ids_json,rationale=excluded.rationale,updated_at=excluded.updated_at', (task_id, decision, json.dumps(note_ids), 'Manual learner decision', stamp, stamp))
        return self.decisions()[task_id]

    def save_coverage_snapshot(self, notes):
        stamp = now()
        with self.lock, self.connect() as db:
            db.execute('DELETE FROM coverage_snapshot')
            db.executemany(
                'INSERT INTO coverage_snapshot(note_id,title,entry_date,content_hash,layer_id,concepts_json,matched_at) VALUES(?,?,?,?,?,?,?)',
                [(note['id'], note['title'], note['entry_date'], note['content_hash'], note['layer_id'], json.dumps(layer_concepts(note['layer_id'])), stamp)
                 for note in notes if note.get('layer_id')]
            )


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def valid_date(value):
    try:
        return date.fromisoformat(value.strip('"\' ')).isoformat()
    except (ValueError, TypeError):
        return None


def layer_concepts(layer_id):
    concepts = {
        1: ['memory hierarchy', 'processes', 'threads', 'virtual memory', 'scheduling'],
        2: ['http request flow', 'dns', 'timeouts', 'observability', 'concurrency'],
        3: ['redis', 'caching', 'event loops', 'freshness', 'eviction'],
        4: ['memory layout', 'cache lines', 'allocation', 'benchmarking'],
        5: ['postgres', 'query planning', 'mvcc', 'wal', 'durability'],
        6: ['queues', 'idempotency', 'leases', 'retries', 'distributed failure'],
        7: ['attention', 'transformers', 'kv cache', 'prefill', 'decode'],
        8: ['inference serving', 'batching', 'ttft', 'itl', 'scheduler'],
        9: ['agent harness', 'replay', 'provenance', 'recovery', 'evaluation'],
    }
    return concepts.get(layer_id, [])


def coverage_for(scanner, store):
    snapshot = scanner.snapshot()
    notes = snapshot['notes']
    if snapshot['status'] != 'unavailable':
        store.save_coverage_snapshot(notes)
    decisions = store.decisions()
    grouped = {layer_id: [] for layer_id in range(1, 10)}
    for note in notes:
        layer_id = note.get('layer_id')
        if layer_id in grouped:
            grouped[layer_id].append({key: note[key] for key in ('id', 'title', 'entry_date', 'content_hash')})
    layers = []
    for layer_id in range(1, 10):
        matches = grouped[layer_id]
        state = 'directly_covered' if matches else 'not_found'
        recommendation = 'review' if matches else 'start_new'
        missing = ['No mapped Sakethwiki notes for this layer.'] if not matches else []
        missing.append('Manual proof task is still required before completion.')
        layers.append({
            'layer_id': layer_id,
            'task_id': f'layer-{layer_id}',
            'coverage_state': state,
            'concepts': layer_concepts(layer_id),
            'notes': matches,
            'missing': missing,
            'recommendation': recommendation,
            'recommendation_label': DECISION_LABELS[recommendation],
            'decision': decisions.get(f'layer-{layer_id}'),
        })
    return {
        'schema_version': 1,
        'scanned_at': snapshot['scanned_at'],
        'status': snapshot['status'],
        'last_success_at': snapshot['last_success_at'],
        'snapshot_id': snapshot['snapshot_id'],
        'layers': layers,
        'warnings': snapshot['warnings'],
    }


def parse_note(raw, slug, modified):
    text = raw.decode('utf-8')
    lines = text.splitlines()
    fields, start = {}, 0
    if lines and lines[0].strip() == '---':
        end = next((i for i, line in enumerate(lines[1:], 1) if line.strip() == '---'), None)
        if end is None:
            raise ValueError('incomplete frontmatter')
        for line in lines[1:end]:
            key, sep, value = line.partition(':')
            if sep and key in ('title', 'date', 'last_updated'):
                fields[key] = value.strip()
        start = end + 1
    body = '\n'.join(lines[start:])
    if not body.strip():
        raise ValueError('empty note')
    title = fields.get('title', '').strip()
    if title[:1] == '"':
        try:
            title = json.loads(title)
        except json.JSONDecodeError:
            title = title.strip('"')
    elif title[:1] == "'":
        title = title.strip("'").replace("''", "'")
    if not title or title in ('|', '>'):
        title = next((line[2:].strip() for line in lines[start:] if line.startswith('# ')), slug)
    # Entry dates describe substantive entries; filesystem timestamps are change hints only.
    entry_dates = [valid_date(m) for m in re.findall(r'^## .*?\b(\d{4}-\d{2}-\d{2})\b', body, re.M)]
    if fields.get('date'):
        entry_dates.append(valid_date(fields['date']))
    return {
        'id': f'_wiki/cs/{slug}.md', 'title': title[:300],
        'entry_date': max((d for d in entry_dates if d), default=None),
        'modified_at': datetime.fromtimestamp(modified, timezone.utc).isoformat(timespec='seconds'),
        'content_hash': hashlib.sha256(raw).hexdigest(),
        'layer_id': LAYER_BY_SLUG.get(slug), 'evidence_state': 'stored',
    }


class Scanner:
    def __init__(self, vault):
        self.vault = Path(vault).expanduser().resolve()
        self.last_success = None
        self.lock = threading.Lock()

    def snapshot(self):
        if not self.lock.acquire(timeout=1):
            return self.result('unavailable', now(), [], ['A scan is already in progress; retry shortly.'])
        try:
            return self._snapshot()
        finally:
            self.lock.release()

    def _snapshot(self):
        scanned_at, notes, warnings = now(), [], []
        started = time.monotonic()
        dir_fd = wiki_fd = None
        try:
            # Open each directory without following symlinks, then open files relative to it.
            flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
            vault_fd = os.open(self.vault, flags)
            try:
                wiki_fd = os.open('_wiki', flags, dir_fd=vault_fd)
            finally:
                os.close(vault_fd)
            dir_fd = os.open('cs', flags, dir_fd=wiki_fd)
            candidates = []
            with os.scandir(dir_fd) as entries:
                for entry in entries:
                    if time.monotonic() - started > SCAN_SECONDS or len(candidates) >= MAX_FILES:
                        warnings.append('Scan limit reached; this snapshot is incomplete.')
                        break
                    name = entry.name
                    if not name.endswith('.md') or not re.fullmatch(r'[\w-]+\.md', name):
                        continue
                    if re.search(r'(^|[-_])(test|fixture|fixtures)([-_.]|$)', name, re.I):
                        continue
                    if entry.is_symlink():
                        warnings.append('A symlink was excluded.')
                        continue
                    candidates.append(name)
            for name in sorted(candidates):
                if time.monotonic() - started > SCAN_SECONDS:
                    warnings.append('Scan time limit reached; this snapshot is incomplete.')
                    break
                fd = None
                try:
                    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dir_fd)
                    before = os.fstat(fd)
                    if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_BYTES:
                        raise ValueError('not a bounded regular file')
                    with os.fdopen(fd, 'rb') as file:
                        fd = None
                        raw = file.read(MAX_BYTES + 1)
                        after = os.fstat(file.fileno())
                    if len(raw) > MAX_BYTES or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                        raise ValueError('note changed while reading')
                    notes.append(parse_note(raw, name[:-3], after.st_mtime))
                except (OSError, ValueError, UnicodeError):
                    warnings.append('A note could not be read completely; retrying on the next refresh.')
                finally:
                    if fd is not None:
                        os.close(fd)
        except OSError:
            return self.result('unavailable', scanned_at, [], ['Learning notes are unavailable. Check the vault location and access.'])
        finally:
            if dir_fd is not None:
                os.close(dir_fd)
            if wiki_fd is not None:
                os.close(wiki_fd)
        notes.sort(key=lambda n: (n['entry_date'] or '', n['id']), reverse=True)
        status = 'partial' if warnings else 'ok'
        if status == 'ok':
            self.last_success = scanned_at
        return self.result(status, scanned_at, notes, list(dict.fromkeys(warnings)))

    def result(self, status, scanned_at, notes, warnings):
        digest = hashlib.sha256(json.dumps(notes, sort_keys=True).encode()).hexdigest()
        return dict(schema_version=1, status=status, scanned_at=scanned_at,
                    last_success_at=self.last_success, snapshot_id=digest, notes=notes, warnings=warnings)


def make_server(vault, port=8768, host='127.0.0.1', store_path=None, allowed_hosts=None):
    if store_path is None and not isinstance(host, str):
        store_path, host = host, '127.0.0.1'
    if allowed_hosts is None:
        allowed_hosts = [name.strip() for name in os.environ.get('APP_ALLOWED_HOSTS', '').split(',') if name.strip()]
    scanner = Scanner(vault)
    store = AppStore(store_path or os.environ.get('APP_STATE_PATH') or BASE / 'data' / 'learning-app.sqlite3')
    assets = {'/': ('index.html', 'text/html'), '/index.html': ('index.html', 'text/html'),
              '/live.js': ('live.js', 'text/javascript'),
              '/manifest.webmanifest': ('manifest.webmanifest', 'application/manifest+json'),
              '/icon.png': ('assets/saketh-learning-icon.png', 'image/png')}

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(8)

        def log_message(self, fmt, *args):
            pass  # Never log private note metadata or request parameters.

        def respond(self, code, body, content_type='application/json'):
            if not isinstance(body, bytes):
                body = json.dumps(body).encode()
            self.send_response(code)
            self.send_header('Content-Type', content_type + '; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', 'DENY')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.end_headers()
            if self.command != 'HEAD':
                self.wfile.write(body)

        def allowed(self):
            port = self.server.server_port
            loopback = {f'127.0.0.1:{port}', f'localhost:{port}'}
            # Tailnet names arrive via `tailscale serve`, which terminates HTTPS on 443.
            tailnet = {name: name for name in allowed_hosts} | {f'{name}:443': name for name in allowed_hosts}
            host = self.headers.get('Host', '')
            origin = self.headers.get('Origin')
            if host in loopback:
                expected_origin = f'http://{host}'
            elif host in tailnet:
                expected_origin = f'https://{tailnet[host]}'
            else:
                expected_origin = None
            if expected_origin is None or (origin and origin != expected_origin) or self.headers.get('Sec-Fetch-Site') == 'cross-site':
                self.respond(403, {'error': 'Cross-origin access denied'})
                return False
            return True

        def read_json(self):
            try:
                size = int(self.headers.get('Content-Length', '0'))
            except ValueError as exc:
                raise ValueError('Invalid request length') from exc
            if size <= 0 or size > 65536:
                raise ValueError('Invalid request length')
            if 'application/json' not in self.headers.get('Content-Type', ''):
                raise ValueError('Expected JSON')
            return json.loads(self.rfile.read(size))

        def do_GET(self):
            if not self.allowed():
                return
            path = urlsplit(self.path).path
            if path == '/health':
                return self.respond(200, {'status': 'ok'})
            if path == '/api/learning-state':
                result = scanner.snapshot()
                return self.respond(503 if result['status'] == 'unavailable' else 200, result)
            if path == '/api/coverage':
                result = coverage_for(scanner, store)
                return self.respond(503 if result['status'] == 'unavailable' else 200, result)
            if path == '/api/decisions':
                return self.respond(200, {'schema_version': 1, 'decisions': store.decisions()})
            if path == '/api/progress':
                return self.respond(200, {'schema_version': 1, **store.progress()})
            if path not in assets:
                return self.respond(404, {'error': 'Not found'})
            filename, kind = assets[path]
            try:
                return self.respond(200, (BASE / filename).read_bytes(), kind)
            except OSError:
                return self.respond(503, {'error': 'Site asset unavailable'})

        do_HEAD = do_GET

        def do_PUT(self):
            if not self.allowed():
                return
            path = urlsplit(self.path).path
            try:
                body = self.read_json()
                if path == '/api/progress':
                    return self.respond(200, {'schema_version': 1, **store.save_progress(body)})
                if path == '/api/decisions':
                    return self.respond(200, {'schema_version': 1, 'decision': store.save_decision(body)})
            except StaleWrite:
                return self.respond(409, {'schema_version': 1, 'error': 'stale_write', **store.progress()})
            except (json.JSONDecodeError, ValueError) as exc:
                return self.respond(400, {'error': str(exc)})
            except sqlite3.Error:
                return self.respond(503, {'error': 'Local app state unavailable'})
            return self.respond(404, {'error': 'Not found'})

        def method_not_allowed(self):
            self.respond(405, {'error': 'Read-only service'})

        do_POST = do_PATCH = do_DELETE = do_OPTIONS = do_TRACE = do_CONNECT = method_not_allowed

    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    return server


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8768)
    parser.add_argument('--host', default=os.environ.get('APP_HOST', '127.0.0.1'))
    parser.add_argument('--vault', default=os.environ.get('VAULT_PATH', '~/SakethVault'))
    parser.add_argument('--state', default=os.environ.get('APP_STATE_PATH'))
    args = parser.parse_args()
    server = make_server(args.vault, args.port, args.host, args.state)
    print(f'Learning roadmap: http://127.0.0.1:{server.server_port}/', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
