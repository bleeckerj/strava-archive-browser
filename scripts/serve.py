"""Serve the archive browser on this computer."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit
import argparse

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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), partial(ProjectHandler, directory=str(PROJECT)))
    print(f'Strava archive browser: http://127.0.0.1:{args.port}/', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
