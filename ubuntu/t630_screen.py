#!/usr/bin/python3
"""Read-only live scanout view. Loopback only; use an authenticated SSH tunnel."""
import ctypes
import fcntl
import http.server
import io
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit
from PIL import Image

ROTATION_STATE = Path('/run/t630-weston-rotation.state')


def orient_for_viewer(image):
    """Undo the panel transform so the remote view follows the tablet UI."""
    try:
        transform = int(ROTATION_STATE.read_text().strip())
    except (OSError, ValueError):
        transform = 1  # Installed default is landscape/rotate-90.
    operations = {
        0: None,
        1: Image.Transpose.ROTATE_270,
        2: Image.Transpose.ROTATE_180,
        3: Image.Transpose.ROTATE_90,
    }
    operation = operations.get(transform, Image.Transpose.ROTATE_270)
    return image if operation is None else image.transpose(operation)


def capture():
    result = subprocess.run(['/usr/local/libexec/t630-capture','--stdout'],
                            check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=8)
    image = Image.open(io.BytesIO(result.stdout))
    if image.size != (1200,1920):
        raise ValueError('Unexpected display dimensions')
    image = orient_for_viewer(image)
    out = io.BytesIO()
    image.save(out,format='PNG',compress_level=3)
    return out.getvalue()

if sys.argv[1:] == ['--snapshot']:
    sys.stdout.buffer.write(capture())
    raise SystemExit(0)
if sys.argv[1:]:
    raise SystemExit('Use --snapshot or no arguments')

service_lock = open('/run/t630-screen-service.lock', 'a')
try:
    fcntl.flock(service_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    raise SystemExit(0)

ctypes.CDLL(None).prctl(15,b't630-screen',0,0,0)
page = b'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Ubuntu tablet - live view</title>
<style>body{margin:0;background:#17111f;color:#eee;font:15px system-ui}header{padding:12px 20px;display:flex;gap:20px;align-items:center}button{padding:6px 14px}img{display:block;width:100%;height:calc(100vh - 60px);object-fit:contain}span{opacity:.7}</style></head>
<body><header><strong>Ubuntu tablet</strong><span id="status">Connecting...</span><button id="toggle">Pause</button><span>View-only \xe2\x80\xa2 encrypted SSH tunnel</span></header><img id="screen" alt="Live tablet display">
<script>let running=true,timer;const img=document.querySelector('#screen'),status=document.querySelector('#status'),button=document.querySelector('#toggle');function next(){if(running)img.src='/frame.png?t='+Date.now()}img.onload=()=>{status.textContent='Updated '+new Date().toLocaleTimeString();timer=setTimeout(next,1500)};img.onerror=()=>{status.textContent='Waiting for tablet display...';timer=setTimeout(next,3000)};button.onclick=()=>{running=!running;clearTimeout(timer);button.textContent=running?'Pause':'Resume';if(running)next()};next();</script></body></html>'''
lock=threading.Lock()
cached=b''
captured_at=0.0
class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def do_GET(self):
        global cached,captured_at
        host=urlsplit('//'+self.headers.get('Host','')).hostname
        if host not in ('127.0.0.1','localhost') or self.headers.get('Sec-Fetch-Site','none') not in ('none','same-origin'):
            self.send_error(403); return
        path=urlsplit(self.path).path
        if path not in ('/','/frame.png'):
            self.send_error(404); return
        try:
            if path=='/': data,mime=page,'text/html; charset=utf-8'
            else:
                with lock:
                    if time.monotonic()-captured_at>1 or not cached:
                        cached=capture();captured_at=time.monotonic()
                    data=cached
                mime='image/png'
            self.send_response(200)
            self.send_header('Content-Type',mime)
            self.send_header('Content-Length',str(len(data)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('X-Frame-Options','DENY')
            self.send_header('Content-Security-Policy',"default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; frame-ancestors 'none'")
            self.end_headers();self.wfile.write(data)
        except (BrokenPipeError,ConnectionResetError): pass
        except Exception as e:
            print(type(e).__name__,flush=True)
            self.send_error(503,'Display not ready')

http.server.ThreadingHTTPServer(('127.0.0.1',8765),Handler).serve_forever()
