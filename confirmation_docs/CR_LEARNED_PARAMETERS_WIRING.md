# WIRING — apply with the gate running (invasive edits held back)

The additive pieces are committed as files: the write capacity
(`mindsos_capacity/builtins/learn_parameter.py`), the snapshot reader
(`mindsos_knowledge/learned_parameters_snapshot.py`), the schema props, the ADR
amendment, and unit tests. The edits below touch boot/dispatch — apply them on
the gate box so any breakage surfaces immediately.

## 1. Export the installer
`mindsos_capacity/builtins/__init__.py` — add to the imports + `__all__`:
    from .learn_parameter import install_learn_parameter_capacities

## 2. Register the capacity at boot
`mindsos_server/boot.py` (~line 98 import block, ~line 107 call block):
    from mindsos_capacity.builtins import install_learn_parameter_capacities
    ...
    install_learn_parameter_capacities(cl)   # alongside install_consolidate_capacities(cl)

## 3. Fill the snapshot at L4Dispatcher construction
Import in each file:
    from mindsos_knowledge.learned_parameters_snapshot import read_learned_parameter_snapshot

- `mindsos_server/boot.py` (~line 316) — add kwarg to the `L4Dispatcher(...)`:
      learned_parameters=read_learned_parameter_snapshot(kl, user),
- `mindsos_intelligence/intelligence_layer.py` (~line 181) — add kwarg:
      learned_parameters=read_learned_parameter_snapshot(self._kl, self._session.user_id),
- `intelligence_layer.py` (~line 220, recovery_dispatcher) — OPTIONAL; crash
  recovery does not consume parameters. Skip unless a recovery body needs them.

Guard: if `session.user_id` can be absent on any path, wrap with a truthy check
and pass `{}` — the reader assumes a valid user.

## 4. Gate (on Linux; py3.11+)
    cd /home/sanmyaku/mindsos
    git worktree add _wt-learn-parameter feat/learn-parameter   # or work in place
    python3 -m pytest tests/learned_parameters -q
    python3 -m pytest -q            # full suite must stay green
