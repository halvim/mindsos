"""Phase 08 — L1 Reconstruction tests.

Covers:

* :func:`mindsos_core.reconstruction.iter_load_graph` (PB-3 A / RPB-1 A
  / RPB-8 A / RPB-10 A / RR-12 A).
* :class:`mindsos_core.reconstruction.MetagraphLoader` + module function
  :func:`load_metagraph` (PB-2 C / RR-5 B / R4-1 A / R4-8 A / R4-11 A
  / PB-6 B / RPB-3 C / RPB-2 A / R4-2 D / R4-7 A+C).
* :class:`mindsos_instances.reconstruction.InstanceLoader` (PB-4 A /
  RR-3 A / RR-4 B).
* ``Metagraph.register_after_load_observer`` plumbing
  (RR-9 A / RPB-9 A).
* 3 new exception classes
  (:class:`RefreshUnsafeError` / :class:`WALReplayerMissingError` /
  :class:`RoleMismatchError`).
* P60 — ``add_metaedge`` / ``add_metahyperedge`` explicit-id kwargs.
* P61 — IntergraphHyperEdge anchor persist fix.
* CLI extensions (``sync --metagraph M``, ``load --metagraph M``,
  ``verify --source=db --metagraph M``, mutex).
"""
