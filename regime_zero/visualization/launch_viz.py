import http.server
import socketserver
import webbrowser
import os
import sys
import threading
import time

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from regime_zero.visualization.prepare_viz_data import prepare_data

PORT = 8000
DIRECTORY = "regime_zero/visualization"

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

def start_server():
    # Refresh data first
    prepare_data()
    
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"🚀 Serving Regime Galaxy at http://localhost:{PORT}/galaxy_view.html")
        print("Press Ctrl+C to stop.")
        httpd.serve_forever()

if __name__ == "__main__":
    try:
        start_server()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped.")
