import json 
from urllib import request, error

BASE_URL = "http://localhost:8001"

def read_book(book_id):
    req = request.Request(
        f"{BASE_URL}/read?book_id={book_id}", method="GET"
    )
    try:
        with request.urlopen(req) as response:
            return json.loads(response.read())
    except error.HTTPError as e:
        return json.loads(e.read())

def write_book(book_id, author, stock):
    data = json.dumps({"book_id": book_id, "author": author, "stock": stock}).encode()
    req = request.Request(
        f"{BASE_URL}/write",
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"}
    )
    with request.urlopen(req) as response:
        return json.loads(response.read())

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
            print(read_book(book_id))
        else:
            print("Inccorect parsing. Example would be: b14 JRR Tolkien 4")

if __name__ == "__main__":
    main()
