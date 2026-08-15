from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
import json
import argparse

class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/read":
            book_id = parse_qs(parsed.query).get("book_id", [None])[0]
            if book_id is None:
                self.send_json(400, {"error": "book_id query param required"})
                return

            book = self.server.inventory.get_book(book_id)
            if book is None:
                self.send_json(404, {"error": f"no book with id '{book_id}'"})
            else:
                self.send_json(200, {"book_id": book_id, **book})

        elif parsed.path == '/read_all':
            books = self.server.inventory.get_all_books()
            if books is None:
                self.send_json(400, {f"error": "no books in inventory"})
            else:
                self.send_json(200, {"count": len(books), "books": books})
        else:
            self.send_json(404, {"error": "not found"})


    def do_POST(self):
        if self.path == "/write":
            length = int(self.headers.get("Content-Length", 0))
            try:
                data = json.loads(self.rfile.read(length))
                book_id, author, stock = data["book_id"], data["author"], data["stock"]
            except (json.JSONDecodeError, KeyError):
                self.send_json(400, {"error": "expected JSON body {book_id, author, stock}"})
                return
            self.server.inventory.write_book(book_id, author, stock)
            self.send_json(200, {"status": "ok", "book_id": book_id})
        else:
            self.send_json(404, {"error": "not found"})

    def send_json(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

class BookInventory:
    def __init__(self, port):
        self.port = port
        self.books = {}
        self.httpdb = None

    def write_book(self, book_id, author, stock):
        self.books[book_id] = {"author": author, "stock": stock}

    def get_book(self, book_id):
        return self.books.get(book_id)

    def get_all_books(self):
        return self.books
 
    def start(self):
        self._httpd = ThreadingHTTPServer(("localhost", self.port), _Handler)
        self._httpd.inventory = self
        print(f"Book inventory serving on http://localhost:{self.port}")
        self._httpd.serve_forever()
 
 
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=9000)
    args = parser.parse_args()
 
    BookInventory(args.port).start()