"""Serve the archive browser on this computer."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit
import argparse
import errno
import os
import signal
import sys

from server_processes import InspectionError
from server_runtime import register_server, show_conflict, show_status, stop_servers

PROJECT = Path(__file__).resolve().parent.parent


class ProjectHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        self.serve_request(super().do_GET)

    def do_HEAD(self):
        self.serve_request(super().do_HEAD)

    def serve_request(self, method):
        parts = Path(unquote(urlsplit(self.path).path)).parts
        if any(part.startswith('.') for part in parts if part != '/') or any(part == 'node_modules' for part in parts):
            self.send_error(404)
            return
        method()

    def list_directory(self, path):
        self.send_error(404)


def serve(port):
    print(f'Starting Strava archive browser at http://127.0.0.1:{port}/', flush=True)
    print(f'Project: {PROJECT}', flush=True)
    try:
        server = ThreadingHTTPServer(('127.0.0.1', port), partial(ProjectHandler, directory=str(PROJECT)))
    except OSError as error:
        if error.errno != errno.EADDRINUSE:
            raise
        show_conflict(PROJECT, port)
        return 1
    record = None
    try:
        actual_port = server.server_port
        record = register_server(PROJECT, actual_port)
        print(f'\nStrava archive browser is running: http://127.0.0.1:{actual_port}/', flush=True)
        print(f'  PID:     {os.getpid()}', flush=True)
        print(f'  Port:    {actual_port}', flush=True)
        print(f'  Record:  {record}', flush=True)
        print('  Status:  npm run status', flush=True)
        print(f'  Stop:    python3 scripts/serve.py stop --port {actual_port}', flush=True)
        print('  Keep this terminal open. Control-C stops this server.\n', flush=True)
        signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    finally:
        server.server_close()
        if record is not None:
            record.unlink(missing_ok=True)
        print(f'Strava archive browser stopped (PID {os.getpid()}).', flush=True)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', nargs='?', default='start', choices=['start', 'status', 'stop'])
    parser.add_argument('--port', type=int, help='Start on this port (default: 8765); filter status/stop to this port.')
    args = parser.parse_args()
    if args.port is not None and not 0 <= args.port <= 65535:
        parser.error('--port must be between 0 and 65535')
    if args.port == 0 and args.command != 'start':
        parser.error('--port 0 is only available for start, to request a free port')
    try:
        if args.command == 'status':
            return show_status(PROJECT, args.port)
        if args.command == 'stop':
            return stop_servers(PROJECT, args.port)
        return serve(8765 if args.port is None else args.port)
    except (InspectionError, OSError) as error:
        print(f'Server {args.command} failed: {error}', file=sys.stderr)
        print('Inspect listeners manually: lsof -nP -iTCP -sTCP:LISTEN', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
