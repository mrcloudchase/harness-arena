"""todoapi: write a small JSON HTTP API. The work must be run to be judged, so a held-out harness exercises it
against the rubric; a deterministic check only confirms the file compiles. (With a scripted test the
deterministic check would be preferred; this benchmark exists to exercise harness judging.)"""
import ast

from hiddenarena.benchmark import Deterministic, Exercise, Task

INSTRUCTION = """Write app.py: a Python 3 program using only the standard library that runs a JSON HTTP server on the \
port in the PORT environment variable and keeps a to-do list in memory.

- POST /todos with {"title": "..."} creates a todo and returns 201 and {"id": 1, "title": "...", "done": false}; ids \
count up from 1. A missing title or a body that is not valid JSON is a 400.
- GET /todos returns 200 and the list of all todos.
- PATCH /todos/<id> with {"done": true|false} updates the todo and returns it.
- DELETE /todos/<id> removes it and returns 204 with no body.
- An unknown id is a 404."""
RUBRIC = (
    "It starts without arguments and listens on the port in PORT.",
    "POST /todos with a title returns 201 and a todo with an id, the title and done=false.",
    "GET /todos returns 200 and a JSON list of every todo created and not deleted.",
    "PATCH /todos/<id> with {\"done\": true} updates the todo and returns it.",
    "DELETE /todos/<id> returns 204 and the todo is gone afterwards.",
    "Unknown ids give 404, and a missing title or invalid JSON gives 400.",
)


def tasks():
    yield Task("api", INSTRUCTION)


def deliverables(task):
    return ["app.py"]


def compiles(task, submission):
    try:
        ast.parse((submission / "app.py").read_text())
        return 1.0, "app.py parses"
    except (OSError, SyntaxError) as e:
        return 0.0, f"app.py does not parse: {e}"


def judges(task):
    return [Deterministic(compiles, "compiles"), Exercise(RUBRIC, min_agreement=0.6)]
