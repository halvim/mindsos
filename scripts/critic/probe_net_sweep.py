"""Probe: network-capable imports across every mindsos_* package, by AST.

Runs against origin/main ead3bd1:
    PYTHONPATH=. python scripts/critic/probe_net_sweep.py
Empty list = no module in any mindsos_* package imports a network-capable
stdlib or provider module. Proves the TREE only — a deployment-supplied
transport callable is outside any tree check, by design. Repr-only;
verdicts live in coordination S118."""
import ast, pathlib

NET = {"urllib", "http", "socket", "ssl", "requests", "httpx", "aiohttp",
       "anthropic", "openai", "websocket", "websockets"}
hits = []
for f in pathlib.Path(".").glob("mindsos_*/**/*.py"):
    try:
        tree = ast.parse(f.read_text())
    except Exception:
        continue
    for n in ast.walk(tree):
        mods = set()
        if isinstance(n, ast.Import):
            mods = {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
            mods = {n.module.split(".")[0]}
        if mods & NET:
            hits.append((str(f), sorted(mods & NET)))
print("== raw output below this line ==")
print(repr(hits))
