"""Exercise real listener ownership, port conflicts, and lifecycle cleanup."""
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from unittest.mock import patch
import contextlib
import io
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / 'scripts'))

from server_processes import Listener, ServerProcess
from server_runtime import stop_servers


def cli(*arguments):
    return subprocess.run(
        [sys.executable, str(PROJECT / 'scripts' / 'serve.py'), *map(str, arguments)],
        cwd=PROJECT, capture_output=True, text=True, timeout=15,
    )


class ServerLifecycleTests(unittest.TestCase):
    def start_server(self, port=0):
        output = tempfile.TemporaryFile(mode='w+')
        self.addCleanup(output.close)
        process = subprocess.Popen(
            [sys.executable, str(PROJECT / 'scripts' / 'serve.py'), '--port', str(port)],
            cwd=PROJECT, stdout=output, stderr=subprocess.STDOUT,
        )

        def cleanup():
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)

        self.addCleanup(cleanup)
        record_path = PROJECT / '.runtime' / 'servers' / f'{process.pid}.json'
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if record_path.exists():
                record = json.loads(record_path.read_text())
                return process, record, record_path, output
            if process.poll() is not None:
                break
            time.sleep(0.02)
        output.seek(0)
        self.fail(f'Server did not start: {output.read()}')

    def test_status_conflict_and_stop_an_unrecorded_instance(self):
        process, record, path, output = self.start_server()
        self.assertEqual(record['pid'], process.pid)
        self.assertEqual(record['project'], str(PROJECT))
        self.assertGreater(record['port'], 0)
        self.assertIn('started_at', record)
        path.unlink()
        status = cli('status', '--port', record['port'])
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertIn(str(process.pid), status.stdout)
        self.assertIn(str(PROJECT), status.stdout)
        self.assertIn(record['url'], status.stdout)
        self.assertIn('Legacy instance', status.stdout)
        duplicate = cli('--port', record['port'])
        self.assertEqual(duplicate.returncode, 1)
        self.assertIn('already in use', duplicate.stdout)
        self.assertIn(str(process.pid), duplicate.stdout)
        self.assertIn(f'stop --port {record["port"]}', duplicate.stdout)
        self.assertNotIn('Traceback', duplicate.stderr)
        stopped = cli('stop', '--port', record['port'])
        self.assertEqual(stopped.returncode, 0, stopped.stderr)
        self.assertIn('Stopped PID', stopped.stdout)
        process.wait(timeout=5)
        output.seek(0)
        self.assertIn('Control-C stops this server', output.read())

    def test_interrupt_removes_record_and_port_can_be_reused(self):
        process, record, path, _ = self.start_server()
        connection = HTTPConnection('127.0.0.1', record['port'], timeout=2)
        connection.request('GET', '/')
        response = connection.getresponse()
        self.assertEqual(response.status, 200)
        response.read()
        connection.close()
        for blocked in ['/.runtime/servers/' + str(process.pid) + '.json', '/node_modules/', '/scripts/']:
            connection = HTTPConnection('127.0.0.1', record['port'], timeout=2)
            connection.request('HEAD', blocked)
            self.assertEqual(connection.getresponse().status, 404, blocked)
            connection.close()
        process.send_signal(signal.SIGINT)
        self.assertEqual(process.wait(timeout=5), 0)
        self.assertFalse(path.exists())
        replacement, _, replacement_path, _ = self.start_server(record['port'])
        replacement.terminate()
        self.assertEqual(replacement.wait(timeout=5), 0)
        self.assertFalse(replacement_path.exists())

    def test_stop_leaves_a_foreign_listener_running(self):
        with ThreadingHTTPServer(('127.0.0.1', 0), SimpleHTTPRequestHandler) as foreign:
            port = foreign.server_port
            conflict = cli('--port', port)
            self.assertEqual(conflict.returncode, 1)
            self.assertIn(str(os.getpid()), conflict.stdout)
            self.assertIn('another program', conflict.stdout)
            result = cli('stop', '--port', port)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('another program', result.stdout)
            self.assertEqual(foreign.socket.getsockname()[1], port)

    def test_rejects_invalid_ports_without_a_traceback(self):
        for arguments in [('--port', '-1'), ('--port', '65536'), ('stop', '--port', '0')]:
            result = cli(*arguments)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn('Traceback', result.stderr)


class ProcessIdentityTests(unittest.TestCase):
    def test_only_accepts_this_projects_exact_python_entrypoint(self):
        process = ServerProcess(Listener(123, 'Python', ['127.0.0.1:8765']),
                                '/usr/bin/python3 scripts/serve.py --port 8765', str(PROJECT), 'start', 'age')
        self.assertTrue(process.belongs_to(PROJECT))
        process.command = f'/usr/bin/python3 {PROJECT / "scripts" / "serve.py"} --port 8765'
        process.directory = '/tmp'
        self.assertTrue(process.belongs_to(PROJECT))
        for command, directory in [
            ('/usr/bin/python3 -m http.server 8765', str(PROJECT)),
            ('/usr/bin/python3 scripts/serve.py', '/tmp/another-project'),
            ('/usr/bin/python3 scripts/other.py', str(PROJECT)),
            ('/bin/echo scripts/serve.py', str(PROJECT)),
        ]:
            process.command, process.directory = command, directory
            self.assertFalse(process.belongs_to(PROJECT), command)

    def test_stop_rechecks_identity_before_sending_any_signal(self):
        listener = Listener(123, 'Python', ['127.0.0.1:8765'])
        known = ServerProcess(listener, '/usr/bin/python3 scripts/serve.py', str(PROJECT), 'old start', 'age')
        reused = ServerProcess(listener, '/usr/bin/python3 scripts/serve.py', str(PROJECT), 'new start', 'age')
        with patch('server_runtime.project_servers', return_value=[known]), \
             patch('server_runtime.inspect_process', return_value=reused), \
             patch('server_runtime.os.kill') as kill, contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, 'changed identity'):
                stop_servers(PROJECT)
            kill.assert_not_called()


if __name__ == '__main__':
    unittest.main()
