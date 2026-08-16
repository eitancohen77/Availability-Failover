import json 
from urllib import request, error

URLs = ["http://localhost:8001", "http://localhost:8002"]

def _request(url, method, path, data=None):
    """
    Checks to see if servers work. The way it does this is by a simple
    request, and sees what the response is. If sever does not work then 
    it responds with 
    """
    json_data = None
    if data is not None:
        json_data = json.dumps(data).encode() if data is not None else None

    req = request.Request(
        f"{url}{path}", data=json_data, method=method,
        headers={"Content-Type": "Application/json"} if json_data else {}
    )
    with request.urlopen(req, timeout=3) as response:
        return json.loads(response.read())

def request_with_failover(method, path, data=None):
    """
    This function helps the client choose a server. If server 1 fails, then it
    tries server 2. If server 2 does not work then either its waiting for standby
    or neither server 1 or 2 work.
    """
    for url in URLs:
        try:
            result = _request(url, method, path, data)
            print(f" (answered by {url})")
            return result
        except (error.URLError, TimeoutError):
            continue
    return {"error": "Server is currently not responding"}

def read_book(book_id):
    return request_with_failover("GET", f"/read?book_id={book_id}")

def write_book(book_id, author, stock):
    return request_with_failover("POST", "/write", {"book_id": book_id, "author": author, "stock": stock})

def read_all_books():
    return request_with_failover("GET", f"/read_all")

def main():
    print("Commands: write <book_id> <author> <stock>  |  read <book_id>  |  quit ")
    while True:
        cmd = input("> ").strip()
        if not cmd:
            continue
        if cmd == "quit":
            break

        api_call = cmd.split()
        method = api_call[0]

        if method == "write" and len(api_call) >= 4:
            book_id = api_call[1]
            author = " ".join(api_call[2:-1])
            stock = api_call[-1]
            print(write_book(book_id, author, int(stock)))
        elif method == "read" and len(api_call) == 2:
            print(read_book(api_call[1]))
        elif method == "read_all":
            print(read_all_books())
        else:
            print("Inccorect parsing. Example would be: b14 JRR Tolkien 4")

if __name__ == "__main__":
    main()
