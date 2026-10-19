"""todoapi: write a small JSON HTTP API. The work has to be run to be judged, which the peer harnesses do themselves.
No deterministic check: with a scripted test one would be added as the anchor."""
from harness_arena.benchmark import Task

INSTRUCTION = """Write app.py: a Python 3 program using only the standard library that runs a JSON HTTP server on the \
port in the PORT environment variable and keeps a to-do list in memory.

- POST /todos with {"title": "..."} creates a todo and returns 201 and {"id": 1, "title": "...", "done": false}; ids \
count up from 1. A missing title or a body that is not valid JSON is a 400.
- GET /todos returns 200 and the list of all todos.
- PATCH /todos/<id> with {"done": true|false} updates the todo and returns it.
- DELETE /todos/<id> removes it and returns 204 with no body.
- An unknown id is a 404."""
CRITERIA = ("The work is a small JSON HTTP server in app.py that keeps a to-do list in memory and listens on the port in the PORT "
            "environment variable. Start it and try it. It should: create a todo with POST /todos {\"title\": ...} returning 201 and "
            "{id, title, done: false} with ids counting up from 1; list todos with GET /todos; update one with PATCH /todos/<id> "
            "{\"done\": true|false}; delete one with DELETE /todos/<id> returning 204; answer 404 for an unknown id and 400 for a "
            "missing title or invalid JSON. More of that working correctly is better; a server that does not start is the worst.")


def tasks():
    yield Task("api", INSTRUCTION)


def deliverables(task):
    return ["app.py"]


def criteria(task):
    return CRITERIA
