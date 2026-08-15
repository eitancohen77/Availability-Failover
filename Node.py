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
            if book_id is None:
                self.send_json(400, {"error": "book_id query param required"})
                return

            status, body = self.server.node.read_book(book_id)
            self.send_json(status, body)

        elif parsed.path == "/read_all":
            status, body = self.server.node.read_all_books()
            self.send_json(status, body)

        elif parsed.path == "/ping":
            self.send_json(200, {"node_id": self.server.node.node_id, "role": self.server.node.role})

        else:
            self.send_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/write":
            self.send_json(404, {"error": "not found"})
            return

        if self.server.node.role != "active":
            self.send_json(403, {"error": "this node is not active, it can't accept writes"})
            return

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

        status, body = self.server.node.write_books(book_id, author, stock)
        self.send_json(status, body)

    def send_json(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class Node:
    """
    The server instance node. Role is either "active" or "standby".
    Book data lives entirely in the inventory server -- parsed_for_inventory
    is the one place that talks to it; write_books/read_book/read_all_books
    all just call through it and hand back the SAME shape it returned:
    (status_code, body).
    """

    def __init__(self, node_id, port, role, inventory_port, primary_port=None, check_interval=5):
        self.node_id = node_id
        self.port = port
        self.role = role
        self.primary_port = primary_port
        self.check_interval = check_interval
        self.inventory_port = inventory_port
        self.http = None

    def parsed_for_inventory(self, method, path, data=None):
        json_data = None
        if data is not None:
            json_data = json.dumps(data).encode()
        req = request.Request(
            f"http://localhost:{self.inventory_port}{path}",
            data=json_data, method=method,
            headers={"Content-Type": "application/json"} if data else {}
        )

        try:
            with request.urlopen(req) as response:
                return response.status, json.loads(response.read())
        except error.HTTPError as e:
            return e.code, json.loads(e.read())

    def write_books(self, book_id, author, stock):
        result = self.parsed_for_inventory(
            "POST", "/write", {"book_id": book_id, "author": author, "stock": stock}
        )
        print(f"RESULTS FROM WRITE_BOOK{result}")
        return result

    def read_book(self, book_id):
        result = self.parsed_for_inventory("GET", f"/read?book_id={book_id}")
        print(f"RESULTS FROM READ_BOOK{result}")
        return result

    def read_all_books(self):
        status, result = self.parsed_for_inventory("GET", "/read_all")
        print(f"RESULTS FROM READ_ALL_BOOK{result}")
        return status, result  # return BOTH -- do_GET needs the status too

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
    parser.add_argument("--inventory-port", type=int, help="Port of the database both servers share", required=True)
    args = parser.parse_args()

    node = Node(args.id, args.port, args.role, inventory_port=args.inventory_port, primary_port=args.primary_port)
    node.start()