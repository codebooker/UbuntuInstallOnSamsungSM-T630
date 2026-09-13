"""Temporary TLS transfer: one fixed non-secret snapshot, one allowed Mac."""
import http.server
import secrets
import shutil
import ssl
import sys
import threading
from pathlib import Path

bind, peer, token = sys.argv[1:]
source = Path('/tmp/desktop-snapshot.tar.gz')

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.client_address[0] != peer or not secrets.compare_digest(self.path, '/'+token):
            self.send_error(403)
            return
        self.send_response(200)
        self.send_header('Content-Type', 'application/gzip')
        self.send_header('Content-Length', str(source.stat().st_size))
        self.end_headers()
        try:
            with source.open('rb') as src:
                shutil.copyfileobj(src, self.wfile, 1024*1024)
            self.wfile.flush()
            print('Snapshot response completed', flush=True)
        finally:
            threading.Thread(target=self.server.shutdown, daemon=True).start()

context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain('/tmp/snapshot-transfer/cert.pem', '/tmp/snapshot-transfer/key.pem')
server = http.server.ThreadingHTTPServer((bind, 8443), Handler)
server.socket = context.wrap_socket(server.socket, server_side=True)
# Hard lifetime bound in case the Mac never connects.
timer = threading.Timer(180, server.shutdown)
timer.daemon = True
timer.start()
server.serve_forever()
server.server_close()
timer.cancel()
