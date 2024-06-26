#!/usr/bin/env python3

import http.server
import socketserver
import os
from pathlib import Path

os.chdir(os.environ["PROJECT_ROOT"])
p = Path("dist/")
if not p.exists():
    print("dist/ not found. Did you forget to build the website?")
    exit(1)
os.chdir(p)

PORT = 27771
Handler = http.server.SimpleHTTPRequestHandler
while True:
    try:
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            print(f"Serving build on http://localhost:{PORT}")
            httpd.serve_forever()
        break
    except OSError:
        PORT += 1
