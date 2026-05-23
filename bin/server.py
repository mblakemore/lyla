#!/usr/bin/env python3
"""
server.py - Simple HTTP server to serve lyla.html and current-state.json

Usage: python3 bin/server.py [--port PORT]
  Default port: 8080
"""

import http.server
import json
import os
import socketserver
import sys
import argparse

PORT_DEFAULT = 8080


class LylaHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler that serves both static files and state JSON."""
    
    def do_GET(self):
        if self.path == '/state/current-state.json':
            try:
                with open('state/current-state.json', 'r') as f:
                    data = json.load(f)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(data).encode())
                return
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(str(e).encode())
                return
        
        super().do_GET()


def main():
    parser = argparse.ArgumentParser(description='Serve lyla.html for holographic visualization')
    parser.add_argument('--port', type=int, default=PORT_DEFAULT, help=f'Port to listen on (default: {PORT_DEFAULT})')
    args = parser.parse_args()
    
    os.chdir(os.path.dirname(os.path.abspath(__file__)) + '/../visualization')
    
    print(f"Lyla server starting at http://localhost:{args.port}")
    print("Press Ctrl+C to stop")
    
    with socketserver.TCPServer(("", args.port), LylaHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


if __name__ == "__main__":
    main()
