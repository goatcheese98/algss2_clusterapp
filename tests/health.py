"""Reject false readiness on real cloud loopback HTTP responses."""
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import subprocess
import threading

parser = argparse.ArgumentParser()
parser.add_argument('--r', default='R')
args = parser.parse_args()

class Handler(BaseHTTPRequestHandler):
    status = 200
    body = b'ALGS shiny-javascript'

    def do_GET(self):
        self.send_response(self.status)
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, *args):
        pass

server = HTTPServer(('127.0.0.1', 0), Handler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
try:
    env = dict(os.environ, PORT=str(server.server_port))
    for status, body, expected in [(200, b'ALGS shiny-javascript', 0),
                                   (503, b'ALGS shiny-javascript', 1), (200, b'other service', 1)]:
        Handler.status, Handler.body = status, body
        result = subprocess.run([args.r, '--slave', '-f', 'scripts/health.R'], env=env, capture_output=True, text=True, timeout=10)
        assert result.returncode == expected, result.stderr
finally:
    server.shutdown()
    server.server_close()
thread.join(timeout=5)
result = subprocess.run([args.r, '--slave', '-f', 'scripts/health.R'], env=env, capture_output=True, text=True, timeout=10)
assert result.returncode == 1
print('Readiness HTTP/503/wrong-service/closed-port tests passed')
