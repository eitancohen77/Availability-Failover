from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import argparse
from urllib.parse import urlparse, parse_qs
import time

class httpServer(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/read":
            self.send_json(404, {"error": "not found"})

        book_id = parse_qs(parsed.query).get("book_id", [None])[0]
        if book_id == None:
            self.send_json(400, {"error": "book_id query param required"})
            return
        
        book = self.server.node.read_book(book_id)
        if book is None:
            self.send_json(400, {f"error": "no book with id: {book_id}"})
        else:
            self.send_json(200, {"book_id": book_id, **book})

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
    """

    def __init__(self, node_id, port):
        self.node_id = node_id
        self.port = port
        self.books = {}
        self.http = None

    def write_books(self, book_id, author, stock):
        self.books[book_id] = {"author": author, "stock": stock}

    def read_book(self, book_id):
        return self.books.get(book_id)


    def start(self):
        self.http = ThreadingHTTPServer(("localhost", self.port), httpServer)
        self.http.node = self

        threading.Thread(target=self.http.serve_forever, daemon=True).start()
        print(f"{self.node_id} Server runnning on http://localhost:{self.port}")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n{self.node_id} Shutting down")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start a single node")
    parser.add_argument("--id", required=True, help="Unique identifier for the node")
    parser.add_argument("--port", type=int, required=True, help="Port to listen on")
    args = parser.parse_args()

    node = Node(args.id, args.port)
    node.start()

    