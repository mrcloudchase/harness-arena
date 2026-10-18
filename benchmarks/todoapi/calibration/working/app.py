import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

todos, ids = {}, [0]


class Handler(BaseHTTPRequestHandler):
    def reply(self, code, body=None):
        data = json.dumps(body).encode() if body is not None else b""
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def body(self):
        try:
            return json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"null")
        except ValueError:
            return None

    def item(self):
        try:
            return todos.get(int(self.path.rsplit("/", 1)[1])) if self.path.startswith("/todos/") else None
        except ValueError:
            return None

    def do_GET(self):
        self.reply(200, list(todos.values())) if self.path == "/todos" else self.reply(404, {"error": "not found"})

    def do_POST(self):
        body = self.body()
        if self.path != "/todos":
            return self.reply(404, {"error": "not found"})
        if not isinstance(body, dict) or not body.get("title"):
            return self.reply(400, {"error": "title required"})
        ids[0] += 1
        todos[ids[0]] = {"id": ids[0], "title": body["title"], "done": False}
        self.reply(201, todos[ids[0]])

    def do_PATCH(self):
        todo, body = self.item(), self.body()
        if todo is None:
            return self.reply(404, {"error": "not found"})
        if not isinstance(body, dict) or not isinstance(body.get("done"), bool):
            return self.reply(400, {"error": "done must be a boolean"})
        todo["done"] = body["done"]
        self.reply(200, todo)

    def do_DELETE(self):
        todo = self.item()
        if todo is None:
            return self.reply(404, {"error": "not found"})
        del todos[todo["id"]]
        self.reply(204)

    def log_message(self, *args):
        pass


HTTPServer(("", int(os.environ["PORT"])), Handler).serve_forever()
