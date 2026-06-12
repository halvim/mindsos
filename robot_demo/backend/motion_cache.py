"""DM-3 — trajectory cache (PB-F / PB-OO, design log §15).

The constrained-order menu (item × source × target × grasp branch) is a
DM-8 concern — combos + the Manager planner don't exist until DM-5/DM-8.
At DM-3 this is the **mechanism** only, seeded with the atomic verified
targets: a keyed store of precomputed frame lists. Demo-time the live
wrapper looks up here first and live-generates only on a miss
(:mod:`live_motion`).

MuJoCo-free (PB-TT). Thread-safe: the generator thread fills it while the
sim thread reads it.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

#: A cache key: (arm, capacity-kind, target-key). ``arm`` is 1/2 (or 0 for
#: the belt); ``kind`` is e.g. "move_to"/"belt"; ``target`` names the
#: discrete verified target (a rest/grasp pose id, a cubby id, a belt mark).
CacheKey = Tuple[int, str, str]

Frames = List[List[List[float]]]


@dataclass
class Trajectory:
    """A cached/generated arm trajectory.

    ``qpos`` (joint-space frames at the capture cadence) is what the live
    tick replays; ``body`` (per-body world poses) is what the atomic
    checklist + pose stream read. ``len`` is the playable length (qpos).
    """

    qpos: List[List[float]]
    body: Frames = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.qpos)


def make_key(arm: int, kind: str, target: str) -> CacheKey:
    return (int(arm), str(kind), str(target))


class TrajectoryCache:
    """In-process keyed store of precomputed trajectories.

    DM-3 scope: in-memory, warmed off the boot critical path (lazy on
    first invoke or a background generator-thread warm). Disk persistence
    + the full order-menu fill are DM-8.
    """

    def __init__(self) -> None:
        self._store: Dict[CacheKey, Frames] = {}
        self._lock = threading.Lock()

    def has(self, key: CacheKey) -> bool:
        with self._lock:
            return key in self._store

    def get(self, key: CacheKey) -> Optional[Frames]:
        with self._lock:
            return self._store.get(key)

    def put(self, key: CacheKey, frames: Frames) -> None:
        with self._lock:
            self._store[key] = frames

    def keys(self) -> Iterable[CacheKey]:
        with self._lock:
            return list(self._store.keys())

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)


__all__ = ["CacheKey", "Frames", "Trajectory", "make_key", "TrajectoryCache"]
