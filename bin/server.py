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
    
    def do_POST(self):
        """Handle control commands from viz_control.py"""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else '{}'
        
        try:
            payload = json.loads(post_data)
        except json.JSONDecodeError:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Invalid JSON'}).encode())
            return
        
        # Command routing based on action field
        action = payload.get('action', '').lower()
        
        if action == 'set_density' or action == 'density':
            count = payload.get('count', 20000)
            try:
                count = int(count)
                with open('visualization/.control_density', 'w') as f:
                    f.write(str(count))
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'ok', 'density': count}).encode())
                return
            except ValueError:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Density must be integer'}).encode())
                return
        
        elif action == 'set_color' or action == 'color':
            color_hex = payload.get('color', '#00ffff')
            try:
                with open('visualization/.control_color', 'w') as f:
                    f.write(color_hex)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'ok', 'color': color_hex}).encode())
                return
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
                return
        
        else:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': f'Unknown action: {action}'}).encode())
            return


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
