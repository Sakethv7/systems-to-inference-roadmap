import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import Scanner, make_server, parse_note

NOTE = b'---\ntitle: "Processes"\ndate: 2026-09-02\n---\n# Processes\n## New entry - 2026-09-03\nSome substantive text.\n'

class ScannerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.cs = self.root / '_wiki/cs'
        self.cs.mkdir(parents=True)
        self.scanner = Scanner(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name='process-state-transitions.md', raw=NOTE):
        p = self.cs / name
        p.write_bytes(raw)
        return p

    def test_dates_mapping_and_repeat(self):
        p = self.write()
        original = p.read_bytes()
        first = self.scanner.snapshot()
        second = self.scanner.snapshot()
        self.assertEqual(first['status'], 'ok')
        self.assertEqual(first['notes'][0]['entry_date'], '2026-09-03')
        self.assertEqual(first['notes'][0]['layer_id'], 1)
        self.assertEqual(first['snapshot_id'], second['snapshot_id'])
        self.assertEqual(p.read_bytes(), original)
        self.assertNotIn(str(self.root), json.dumps(first))

    def test_unmapped_notes_are_visible_and_tests_excluded(self):
        self.write('new-unknown-topic.md')
        self.write('test-example.md')
        self.write('example.md.bak')
        snapshot = self.scanner.snapshot()
        self.assertEqual(len(snapshot['notes']), 1)
        self.assertIsNone(snapshot['notes'][0]['layer_id'])

    def test_symlink_never_reads_outside(self):
        outside = self.root / 'private.md'
        outside.write_text('DO NOT EXPOSE')
        (self.cs / 'escape.md').symlink_to(outside)
        data = self.scanner.snapshot()
        self.assertEqual(data['status'], 'partial')
        self.assertEqual(data['notes'], [])
        self.assertNotIn('DO NOT EXPOSE', json.dumps(data))

    def test_symlink_directory_is_unavailable(self):
        self.cs.rmdir()
        self.cs.symlink_to(self.root, target_is_directory=True)
        self.assertEqual(self.scanner.snapshot()['status'], 'unavailable')

    def test_partial_then_recovery(self):
        p = self.write(raw=b'---\ntitle: unfinished')
        self.assertEqual(self.scanner.snapshot()['status'], 'partial')
        p.write_bytes(NOTE)
        self.assertEqual(self.scanner.snapshot()['status'], 'ok')

    def test_missing_vault_retains_success_time(self):
        self.write()
        good = self.scanner.snapshot()
        self.cs.rename(self.cs.with_name('gone'))
        data = self.scanner.snapshot()
        self.assertEqual(data['status'], 'unavailable')
        self.assertEqual(data['last_success_at'], good['last_success_at'])

    def test_bounds(self):
        self.write()
        self.write('another.md')
        with patch('server.MAX_FILES', 1):
            self.assertEqual(self.scanner.snapshot()['status'], 'partial')
        with patch('server.MAX_BYTES', 10):
            data = self.scanner.snapshot()
            self.assertEqual(data['status'], 'partial')
            self.assertEqual(data['notes'], [])

    def test_unknown_dates_not_replaced_with_mtime(self):
        n = parse_note(b'# Undated\nAn explanation', 'undated', 0)
        self.assertIsNone(n['entry_date'])

    def test_concurrent_scan_is_bounded(self):
        self.scanner.lock.acquire()
        try:
            self.assertEqual(self.scanner.snapshot()['status'], 'unavailable')
        finally:
            self.scanner.lock.release()
        self.assertEqual(self.scanner.snapshot()['status'], 'ok')

    def test_stable_order_and_restart(self):
        self.write('a.md')
        self.write('b.md')
        self.assertEqual(self.scanner.snapshot()['snapshot_id'], Scanner(self.root).snapshot()['snapshot_id'])

    def test_file_disappears_during_scan(self):
        self.write()
        import os
        original = os.open
        def disappearing(path, *args, **kwargs):
            if path == 'process-state-transitions.md':
                raise FileNotFoundError()
            return original(path, *args, **kwargs)
        with patch('server.os.open', side_effect=disappearing):
            self.assertEqual(self.scanner.snapshot()['status'], 'partial')

class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        (Path(cls.temp.name) / '_wiki/cs').mkdir(parents=True)
        cls.server = make_server(cls.temp.name, 0, Path(cls.temp.name) / 'app.sqlite3')
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.temp.cleanup()

    def request(self, method, path, headers=None, body=None):
        c = http.client.HTTPConnection('127.0.0.1', self.server.server_port)
        c.request(method, path, body=body, headers=headers or {})
        r = c.getresponse()
        status, body, headers = r.status, r.read(), dict(r.getheaders())
        c.close()
        return status, body, headers

    def test_allowlist_and_head(self):
        for path in ('/', '/live.js', '/health', '/api/learning-state'):
            self.assertEqual(self.request('GET', path)[0], 200)
        for path in ('/api/coverage', '/api/decisions', '/api/progress'):
            self.assertEqual(self.request('GET', path)[0], 200)
        for path in ('/server.py', '/docs/architecture.md', '/../server.py', '/%2e%2e/server.py', '/Users/private'):
            self.assertEqual(self.request('GET', path)[0], 404)
        self.assertEqual(self.request('HEAD', '/')[1], b'')

    def test_source_edit_is_live_without_restart(self):
        note = Path(self.temp.name) / '_wiki/cs/process-state-transitions.md'
        try:
            note.write_bytes(NOTE)
            first = json.loads(self.request('GET', '/api/learning-state')[1])
            note.write_bytes(NOTE.replace(b'"Processes"', b'"Updated processes"'))
            second = json.loads(self.request('GET', '/api/learning-state')[1])
            self.assertNotEqual(first['snapshot_id'], second['snapshot_id'])
            self.assertEqual(second['notes'][0]['title'], 'Updated processes')
        finally:
            note.unlink(missing_ok=True)

    def test_private_origins_and_mutations(self):
        self.assertEqual(self.request('GET', '/', {'Host': 'evil.example'})[0], 403)
        self.assertEqual(self.request('GET', '/', {'Origin': 'https://evil.example'})[0], 403)
        self.assertEqual(self.request('GET', '/', {'Sec-Fetch-Site': 'cross-site'})[0], 403)
        for method in ('POST', 'PATCH', 'DELETE', 'OPTIONS'):
            self.assertEqual(self.request(method, '/api/learning-state')[0], 405)
        self.assertNotIn('Access-Control-Allow-Origin', self.request('GET', '/')[2])
        self.assertEqual(self.request('GET', '/')[2]['Cache-Control'], 'no-store')

    def test_invalid_writes_are_rejected(self):
        headers = {'Content-Type': 'application/json'}
        self.assertEqual(self.request('PUT', '/api/progress', headers, b'{}')[0], 400)
        bad_progress = {'checkpoints': [{'done': True}], 'quiz_attempts': {}}
        self.assertEqual(self.request('PUT', '/api/progress', headers, json.dumps(bad_progress).encode())[0], 400)
        bad_decision = {'task_id': 'layer-1', 'decision': 'auto_complete', 'note_ids': []}
        self.assertEqual(self.request('PUT', '/api/decisions', headers, json.dumps(bad_decision).encode())[0], 400)
        good_decision = {'task_id': 'layer-1', 'decision': 'review', 'note_ids': ['../../secret.md']}
        self.assertEqual(self.request('PUT', '/api/decisions', headers, json.dumps(good_decision).encode())[0], 400)
        checkpoints = [{'done': False, 'completed_at': None} for _ in range(36)]
        bad_evidence = {'checkpoints': checkpoints, 'quiz_attempts': {}, 'evidence_notes': {'unknown': 'x'}}
        self.assertEqual(self.request('PUT', '/api/progress', headers, json.dumps(bad_evidence).encode())[0], 400)
        long_evidence = {'checkpoints': checkpoints, 'quiz_attempts': {}, 'evidence_notes': {'layer-1-task-2': 'x' * 5001}}
        self.assertEqual(self.request('PUT', '/api/progress', headers, json.dumps(long_evidence).encode())[0], 400)

    def test_progress_and_decision_persist_after_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / '_wiki/cs').mkdir(parents=True)
            store = root / 'learning.sqlite3'
            server = make_server(root, 0, store)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                def call(method, path, payload=None):
                    c = http.client.HTTPConnection('127.0.0.1', server.server_port)
                    headers = {'Content-Type': 'application/json'} if payload is not None else {}
                    body = json.dumps(payload).encode() if payload is not None else None
                    c.request(method, path, body=body, headers=headers)
                    r = c.getresponse()
                    data = r.read()
                    status = r.status
                    c.close()
                    return status, data
                checkpoints = [{'done': index == 0, 'completed_at': '2026-09-11T12:00:00Z' if index == 0 else None} for index in range(36)]
                payload = {
                    'checkpoints': checkpoints,
                    'quiz_attempts': {'layer-1': {'task-0': {'answer': 'true'}}},
                    'evidence_notes': {'layer-1-task-2': 'stride | ns\n1 | 2\n8 | 7'}
                }
                self.assertEqual(call('PUT', '/api/progress', payload)[0], 200)
                self.assertEqual(call('PUT', '/api/decisions', {'task_id': 'layer-1', 'decision': 'review', 'note_ids': []})[0], 200)
            finally:
                server.shutdown()
                server.server_close()
                thread.join()
            restarted = make_server(root, 0, store)
            thread = threading.Thread(target=restarted.serve_forever, daemon=True)
            thread.start()
            try:
                c = http.client.HTTPConnection('127.0.0.1', restarted.server_port)
                c.request('GET', '/api/progress')
                progress = json.loads(c.getresponse().read())
                c.close()
                c = http.client.HTTPConnection('127.0.0.1', restarted.server_port)
                c.request('GET', '/api/decisions')
                decisions = json.loads(c.getresponse().read())
                c.close()
                self.assertTrue(progress['checkpoints'][0]['done'])
                self.assertEqual(progress['quiz_attempts']['layer-1']['task-0']['answer'], 'true')
                self.assertEqual(progress['evidence_notes']['layer-1-task-2'], 'stride | ns\n1 | 2\n8 | 7')
                self.assertEqual(decisions['decisions']['layer-1']['decision'], 'review')
            finally:
                restarted.shutdown()
                restarted.server_close()
                thread.join()

    def test_unlisted_tailnet_host_is_rejected_by_default(self):
        self.assertEqual(self.request('GET', '/', {'Host': 'mac.tail1234.ts.net'})[0], 403)

    def test_manifest_and_icon_are_served(self):
        status, body, headers = self.request('GET', '/manifest.webmanifest')
        self.assertEqual(status, 200)
        self.assertTrue(headers['Content-Type'].startswith('application/manifest+json'))
        self.assertEqual(json.loads(body)['display'], 'standalone')
        status, body, headers = self.request('GET', '/icon.png')
        self.assertEqual(status, 200)
        self.assertTrue(headers['Content-Type'].startswith('image/png'))
        self.assertTrue(body.startswith(b'\x89PNG'))

    def test_stale_progress_write_is_rejected(self):
        headers = {'Content-Type': 'application/json'}
        checkpoints = [{'done': False, 'completed_at': None} for _ in range(36)]
        def put(extra):
            payload = {'checkpoints': checkpoints, 'quiz_attempts': {}, 'evidence_notes': {}, **extra}
            status, body, _ = self.request('PUT', '/api/progress', headers, json.dumps(payload).encode())
            return status, json.loads(body)
        status, first = put({})
        self.assertEqual(status, 200)
        base = first['updated_at']
        status, second = put({'base_updated_at': base})
        self.assertEqual(status, 200)
        self.assertNotEqual(second['updated_at'], base)
        checkpoints[0] = {'done': True, 'completed_at': '2026-09-22T12:00:00Z'}
        status, stale = put({'base_updated_at': base})
        self.assertEqual(status, 409)
        self.assertEqual(stale['error'], 'stale_write')
        self.assertEqual(stale['updated_at'], second['updated_at'])
        self.assertFalse(stale['checkpoints'][0]['done'])
        self.assertFalse(json.loads(self.request('GET', '/api/progress')[1])['checkpoints'][0]['done'])
        self.assertEqual(put({'base_updated_at': 42})[0], 400)
        checkpoints[0] = {'done': False, 'completed_at': None}

    def test_coverage_uses_metadata_not_note_body(self):
        note = Path(self.temp.name) / '_wiki/cs/process-state-transitions.md'
        note.write_bytes(NOTE + b'\nPRIVATE BODY SHOULD NOT LEAK')
        status, body, _ = self.request('GET', '/api/coverage')
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertEqual(data['layers'][0]['coverage_state'], 'directly_covered')
        self.assertIn('_wiki/cs/process-state-transitions.md', json.dumps(data))
        self.assertNotIn('PRIVATE BODY SHOULD NOT LEAK', json.dumps(data))

class AllowedHostTests(unittest.TestCase):
    HOST = 'mac.tail1234.ts.net'

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        (Path(self.temp.name) / '_wiki/cs').mkdir(parents=True)
        self.server = make_server(self.temp.name, 0, '127.0.0.1', Path(self.temp.name) / 'app.sqlite3', allowed_hosts=[self.HOST])
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def status(self, headers):
        c = http.client.HTTPConnection('127.0.0.1', self.server.server_port)
        c.request('GET', '/api/progress', headers=headers)
        status = c.getresponse().status
        c.close()
        return status

    def test_allowlisted_host_requires_https_origin(self):
        self.assertEqual(self.status({'Host': self.HOST}), 200)
        self.assertEqual(self.status({'Host': f'{self.HOST}:443'}), 200)
        self.assertEqual(self.status({'Host': self.HOST, 'Origin': f'https://{self.HOST}'}), 200)
        self.assertEqual(self.status({'Host': self.HOST, 'Origin': f'http://{self.HOST}'}), 403)
        self.assertEqual(self.status({'Host': 'other.tail1234.ts.net'}), 403)
        self.assertEqual(self.status({'Host': self.HOST, 'Sec-Fetch-Site': 'cross-site'}), 403)

    def test_loopback_still_works_with_allowlist(self):
        self.assertEqual(self.status({}), 200)
        self.assertEqual(self.status({'Origin': f'http://127.0.0.1:{self.server.server_port}'}), 200)


if __name__ == '__main__':
    unittest.main()
