# Availability Failover Demo

A small demo of active-passive failover, built entirely with Python's
standard library (no frameworks, no installed database).

![alt text](image.png)

## What's here

- **`BookInventory.py`** — a makeshift "database" standalone server that holds book records
  (`book_id -> {author, stock}`). This is the single source of truth.
  It has no concept of "active" or "standby" — it just stores data.
- **`Node.py`** — the `Node` server. Two of these run at once: one
  `active`, one `standby`. Neither stores book data itself — every
  read/write is forwarded to `BookInventory.py`. The standby also
  watches the active via `/ping`; if the active stops answering, the
  standby promotes itself.
- **`Client.py`** — a terminal client. It tries the primary node's
  address first and falls back to the secondary if the primary doesn't
  answer, so it keeps working across a failover. Its not the client's job to know which server works or not. 

## Why data lives outside the nodes

If book data were stored inside each `Node`, killing the active node
would lose whatever it hadn't shared with the standby. Instead, both
nodes point at the same `BookInventory.py` process. When a node dies,
the data was never inside it to begin with — nothing to lose, nothing
to hand off.

## Running it

```
Open up 4 terminals and in each:

python book_inventory.py --port 9000

python node.py --id A --port 8001 --role active --inventory-port 9000

python node.py --id B --port 8002 --role standby --primary-port 8001 --inventory-port 9000

python client.py
```

Kill node A and watch node B's terminal print that it's taking over.
The client keeps working against port 8002 without you touching it.

## How the server works: `http.server`, `BaseHTTPRequestHandler`, and `do_GET`

`Node.py` and `BookInventory.py` both use Python's built-in
[`http.server`](https://docs.python.org/3/library/http.server.html)
module. No install needed — it's part of the standard library.

### The basic idea

You subclass `BaseHTTPRequestHandler`, and for every request that comes
in, the library automatically calls a method named after the HTTP verb:

- a `GET` request → calls `do_GET(self)`
- a `POST` request → calls `do_POST(self)`

You never call `do_GET` yourself. It's invoked *for* you, once per
incoming request, by the server machinery. Your job is just to fill in
what should happen when it's called.

### Walking through `do_GET`

```python
def do_GET(self):
    parsed = urlparse(self.path)
    if parsed.path == "/read":
        book_id = parse_qs(parsed.query).get("book_id", [None])[0]
        ...
```

- **`self.path`** — the raw path and query string the client requested,
  e.g. `/read?book_id=b1`. It's just a string. `urlparse` and
  `parse_qs` are ordinary standard-library helpers for pulling it apart
  into the path (`/read`) and the query parameters (`book_id=b1`).
- **`if parsed.path == "/read"`** — since one handler covers *every*
  possible URL, you're responsible for routing: checking which path was
  requested and deciding what to do. There's no framework doing this
  for you — it's a plain `if`/`elif` chain.
- **`self.server`** — this is how the handler reaches back into the
  running server. On its own, a handler only knows about the current
  request; `self.server` is the shared server object every request's
  handler can see. That's why, in `start()`, we do:

  ```python
  self.http.node = self  # or self._httpd.inventory = self
  ```

  which stashes the `Node` (or `BookInventory`) instance onto the
  server object, so any handler can reach it via `self.server.node`.
- **Sending a response** — a handler builds its response manually:
  `self.send_response(status_code)` sets the status line,
  `self.send_header(...)` adds headers, `self.end_headers()` closes the
  header section, and `self.wfile.write(body)` writes the actual bytes.
  `send_json` in this project is just a small helper that does all four
  steps at once so it isn't repeated in every branch.

### One handler instance per request

Every time a request comes in, `http.server` creates a **new** handler
instance to deal with it — `do_GET`/`do_POST` only ever see the one
request they were created for. Combined with `ThreadingHTTPServer`
(instead of the plain `HTTPServer`), each of those instances runs on
its own thread, so the server can be handling multiple requests — like
the standby's `/ping` check and a client's `/read` — at the same time
without one blocking the other.