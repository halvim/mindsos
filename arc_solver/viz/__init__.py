"""arc-viz — the ARC intelligence's human/machine communication capacities.

Two L3 capacities in the ``communication`` category, orchestrated by the same L4
as the solver: ``ingest_solve`` (solver output DataStates -> a general expressible
record) and ``express`` (record -> a communication artifact). Code-independent of
the solver: consumes the ``arc.*`` DataStates by IRI, imports nothing from
``arc_solver.spike``. See ARC_VIZ_CONTRACT_SPEC.md.
"""
