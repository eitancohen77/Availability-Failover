from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import argparse
from urllib.parse import urlparse, parse_qs
import time
from urllib import request, error

class httpServer(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/read":
            book_id = parse_qs(parsed.query).get("book_id", [None])[0]
            if book_id == None:
                self.send_json(400, {"error": "book_id query param required"})
                return
            
            book = self.server.node.read_book(book_id)
            if book is None:
                self.send_json(400, {f"error": "no book with id: {book_id}"})
            else:
                self.send_json(200, {"book_id": book_id, **book})

        elif parsed.path == '/read_all':
            books = self.server.node.read_all_books()
            if books is None:
                self.send_json(400, {f"error": "no books in inventory"})
            else:
                self.send_json(200, {"count": len(books), "books": books})
        elif parsed.path == "/ping":
            self.send_json(200, {"node_id": self.server.node.node_id, "role": self.server.node.role})
        
        else:
            self.send_json(404, {"error": "not found"})
            

    def do_POST(self):
        if self.path != "/write":
            self.send_json(404, {"error": "not found"})

        length = int(self.headers.get("Content-Length", 0))
        try:
            data = json.loads(self.rfile.read(length))
            book_id, author, stock = (
                data["book_id"],
                data["author"],
                data["stock"]
            )
        except (json.JSONDecodeError, KeyError):
            self.send_json(400, {"error": "expected JSON body {book_id, author, stock}"})
            return
        self.server.node.write_books(book_id, author, stock)
        self.send_json(200, {"status": "ok", "book_id": book_id})

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
    role - the role that the nodes you initalize will play. Could either be active or 
    standby. 
    """

    def __init__(self, node_id, port, role, primary_port=None, check_interval=5):
        self.node_id = node_id
        self.port = port
        self.role = role
        self.primary_port = primary_port
        self.check_interval = check_interval
        self.books = {}
        self.http = None

    def write_books(self, book_id, author, stock):
        self.books[book_id] = {"author": author, "stock": stock}

    def read_book(self, book_id):
        return self.books.get(book_id)

    def read_all_books(self):
        return self.books

    def is_primary_alive(self):
        # This attempts to ping the primary node
        try:
            request.urlopen(f"http://localhost:{self.primary_port}/ping", timeout=2)
            return True
        except error.URLError:
            return False

    def watch_peer(self):
        while self.role == "standby":
            time.sleep(self.check_interval)
            if self.is_primary_alive() == False:
                print(f"\n[{self.node_id}] Primary node is not responding. TAKING OVER AS ACTIVE!")
                self.role = "active"

    def start(self):
        self.http = ThreadingHTTPServer(("localhost", self.port), httpServer)
        self.http.node = self

        threading.Thread(target=self.http.serve_forever, daemon=True).start()
        print(f"{self.node_id} Server runnning on http://localhost:{self.port}")

        if self.role == "standby":
            self.watch_peer()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n{self.node_id} Shutting down")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start a single node")
    parser.add_argument("--id", required=True, help="Unique identifier for the node")
    parser.add_argument("--port", type=int, required=True, help="Port to listen on")
    parser.add_argument("--role", choices=["active", "standby"], required=True)
    parser.add_argument("--primary-port", type=int, help="The primary node's port (required for standby)")
    args = parser.parse_args()

    node = Node(args.id, args.port, args.role, primary_port=args.primary_port)
    node.start()

    