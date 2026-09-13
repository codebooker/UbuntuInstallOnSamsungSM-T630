#!/usr/bin/python3
"""Normal-user client: bounded brightness/idle controls, never privilege escalation."""
import json
import os
import socket
import stat
import sys

args = sys.argv[1:]
if args == ['status']:
    request = 'STATUS'
elif args == ['inhibit']:
    request = 'INHIBIT'
elif len(args) == 2 and args[0] in ('brightness', 'idle') and args[1].isdigit():
    request = args[0].upper() + ' ' + args[1]
else:
    raise SystemExit('Usage: t630-display status|brightness PERCENT|idle SECONDS|inhibit')
path = '/run/t630-display.sock'
info = os.lstat(path)
if not stat.S_ISSOCK(info.st_mode) or info.st_uid != 0:
    raise SystemExit('Unexpected display service')
with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
    connection.settimeout(2)
    connection.connect(path)
    connection.sendall((request + '\n').encode())
    reply = bytearray()
    while not reply.endswith(b'\n') and len(reply) < 1024:
        chunk = connection.recv(1024 - len(reply))
        if not chunk:
            raise SystemExit('Display service disconnected')
        reply.extend(chunk)
    result = json.loads(reply)
    if 'error' in result:
        raise SystemExit(result['error'])
    print(json.dumps(result))
