"""FalkorDB connection configuration (Phase 07).

Per P5 → P15 A hybrid (env wins; manifest fallback for host-side
``confirm-phase`` runs) + P67 A per-field precedence rules:

* ``host``     — env ``FALKORDB_HOST``  → manifest ``[falkordb] host``  → default.
* ``port``     — env ``FALKORDB_PORT``  → manifest ``[falkordb] port``  → default.
* ``password`` — env ``FALKORDB_PASSWORD`` ONLY (P15 A — never manifest;
  security). Default empty string / None.
* ``graph``    — manifest ``[falkordb] graph`` → default. **No env var**
  per P86 B (graph is a per-call FalkorDB parameter, not a connection-time
  env).

``username`` is NOT surfaced — FalkorDB-Redis auth has no username concept
(P86 B). If a future ACL-enabled deployment needs one, extend the config.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib  # type: ignore[no-redef]


#: Default values when neither env nor manifest provide a value.
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 6379
DEFAULT_GRAPH = "mindsos"


@dataclass(frozen=True)
class FalkorConfig:
    """Connection parameters for :class:`FalkorClient`.

    Frozen for safety — every connection gets its own instance built
    via ``from_env`` / ``from_manifest`` / ``from_env_and_manifest``.
    """

    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    password: Optional[str] = None
    graph: str = DEFAULT_GRAPH

    @classmethod
    def from_env(cls) -> "FalkorConfig":
        """Build from environment variables only.

        Missing env vars fall through to dataclass defaults. ``port`` is
        parsed as int; a malformed ``FALKORDB_PORT`` falls through to
        :data:`DEFAULT_PORT` (warning emitted lazily by doctor self-test
        per P59 A — config never raises here).
        """
        port_str = os.environ.get("FALKORDB_PORT")
        try:
            port = int(port_str) if port_str else DEFAULT_PORT
        except ValueError:
            port = DEFAULT_PORT
        return cls(
            host=os.environ.get("FALKORDB_HOST") or DEFAULT_HOST,
            port=port,
            password=os.environ.get("FALKORDB_PASSWORD") or None,
            graph=DEFAULT_GRAPH,  # graph never comes from env per P86 B
        )

    @classmethod
    def from_manifest(cls, manifest_path: Path) -> "FalkorConfig":
        """Build from ``[falkordb]`` section of a manifest TOML file.

        Returns dataclass defaults when:
          * The file does not exist.
          * The file has no ``[falkordb]`` section.

        Per P15 A the manifest never carries a password; if a future
        manifest does, this loader silently ignores it (env-only rule).
        """
        if not manifest_path.exists():
            return cls()
        with manifest_path.open("rb") as fh:
            data = tomllib.load(fh)
        section = data.get("falkordb") or {}
        return cls._from_mapping(section)

    @classmethod
    def from_env_and_manifest(
        cls, manifest_path: Optional[Path] = None
    ) -> "FalkorConfig":
        """Per-field precedence: env-then-manifest-then-default (P67 A).

        Password is env-only (P15 A) — manifest password fields are
        ignored.
        """
        manifest_section: Mapping[str, Any] = {}
        if manifest_path is not None and manifest_path.exists():
            with manifest_path.open("rb") as fh:
                manifest_section = tomllib.load(fh).get("falkordb") or {}

        # Per-field merge.
        env_host = os.environ.get("FALKORDB_HOST")
        env_port_str = os.environ.get("FALKORDB_PORT")
        env_password = os.environ.get("FALKORDB_PASSWORD")

        host = env_host or manifest_section.get("host") or DEFAULT_HOST

        if env_port_str:
            try:
                port = int(env_port_str)
            except ValueError:
                port = DEFAULT_PORT
        else:
            port_from_manifest = manifest_section.get("port")
            port = (
                int(port_from_manifest)
                if isinstance(port_from_manifest, (int, str))
                else DEFAULT_PORT
            )

        # Password env-only per P15 A.
        password = env_password or None

        # Graph never from env per P86 B.
        graph = manifest_section.get("graph") or DEFAULT_GRAPH

        return cls(host=host, port=port, password=password, graph=graph)

    @classmethod
    def _from_mapping(cls, section: Mapping[str, Any]) -> "FalkorConfig":
        host = section.get("host") or DEFAULT_HOST
        port_value = section.get("port")
        try:
            port = int(port_value) if port_value is not None else DEFAULT_PORT
        except (TypeError, ValueError):
            port = DEFAULT_PORT
        return cls(
            host=host,
            port=port,
            password=None,  # manifest never provides password
            graph=section.get("graph") or DEFAULT_GRAPH,
        )


__all__ = [
    "DEFAULT_HOST",
    "DEFAULT_PORT",
    "DEFAULT_GRAPH",
    "FalkorConfig",
]
