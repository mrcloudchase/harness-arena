"""Which HumanEval problems does a model fail on its own? Run:  HUMANEVAL_PATH=... python benchmarks/humaneval/screen.py deepseek-chat

Asks the model, with no harness, to complete every problem once, checks the answer with the benchmark's hidden tests, and prints
the failing ids as HUMANEVAL_IDS. A screen that uses no harness favours none of them."""
import asyncio
import os
import re
import sys
import tempfile
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent))
import benchmark as he  # noqa: E402


async def attempt(client, model, task):
    for tries in range(4):
        try:
            reply = await attempt_once(client, model, task)
            break
        except httpx.HTTPError:
            await asyncio.sleep(2 ** tries)
    else:
        raise RuntimeError(f"{task.id}: the model could not be reached")
    text = reply.json()["choices"][0]["message"]["content"]
    code = re.search(r"```(?:python)?\n(.*?)```", text, re.S)
    with tempfile.TemporaryDirectory() as work:
        Path(work, "solution.py").write_text(code.group(1) if code else text)
        return he.check(task, Path(work))[0] == 1


async def attempt_once(client, model, task):
    return await client.post("https://api.deepseek.com/v1/chat/completions", headers={"Authorization": f"Bearer {os.environ['DEEPSEEK_API_KEY']}"},
                              json={"model": model, "temperature": 0, "messages": [{"role": "user", "content":
                                    "Complete this Python function. Reply with the complete code in one code block.\n\n" + task.files["solution.py"]}]})


async def main(model):
    sem = asyncio.Semaphore(6)
    tasks = list(he.tasks())
    async with httpx.AsyncClient(timeout=120) as client:
        async def one(t):
            async with sem:
                return t.id, await attempt(client, model, t)
        results = await asyncio.gather(*(one(t) for t in tasks))
    failed = [i for i, ok in results if not ok]
    print(f"{len(failed)} of {len(tasks)} failed")
    print("HUMANEVAL_IDS=" + ",".join(failed))

asyncio.run(main(sys.argv[1]))
