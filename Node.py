from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import argparse

class httpServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_json(200, {
            "message": f"Hello from Node {self.server.node.node_id}",
            "book_count": len(self.server.node.books)
        })

    def send_json(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

class Node:
    """
    The server instance node. Over here is where we will be calling both servers
    """

    def __init__(self, node_id, port):
        self.node_id = node_id
        self.port = port
        self.books = {}
        self.http = None

    def start(self):
        self.http = ThreadingHTTPServer(("localhost", self.port), httpServer)
        self.http.node = self

        threading.Thread(target=self.http.serve_forever, daemon=True).start()
        print(f"{self.node_id} Server runnning on http://localhost:{self.port}")

        try:
            while True:
                pass
        except KeyboardInterrupt:
            print(f"\n{self.node_id} Shutting down")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start a single node")
    parser.add_argument("--id", required=True, help="Unique identifier for the node")
    parser.add_argument("--port", type=int, required=True, help="Port to listen on")
    args = parser.parse_args()

    node = Node(args.id, args.port)
    node.start()

    