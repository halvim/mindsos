"""Resident-brain boot helper.

Composes the durable L2/L3/L4/L5 stack a long-lived process holds: a
Falkor-backed KnowledgeLayer, a CapacityLayer with builtins + installed
skills reactivated, the user's Local booted, and an Orchestrator over a
MentalModel. This is the product-code promotion of the test-only
``tests/phase_49/integration_c.py::build_stack`` recipe (RESIDENT_BRAIN
design note, PB-2), extended with the durable path (PB-3=B):

``bootstrap_kl_from_falkordb`` → install builtins → ``apply_installed_skills``
→ ``boot_local``.

``client=None`` selects the in-memory ephemeral path (deterministic,
Falkor-free) for tests and quick trials — builtins only, no installed
skills, an in-memory persister.

The caller owns the ``client`` lifecycle (open / close) per Phase 07 P4 A;
:func:`boot_brain` never closes it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

log = logging.getLogger(__name__)


@dataclass
class Stack:
    """One live resident-brain instance."""

    kl: Any
    cl: Any
    mm: Any
    dispatcher: Any
    orch: Any
    session: Any
    persister: Any
    user: str
    #: Boot-time :class:`~mindsos_server.skills.ActivationReport` for
    #: installed-skill activation (``None`` on the ephemeral path, which
    #: activates no installed skills). Its ``skipped`` roster names any
    #: bundle a REPL/operator surface should report as unactivated.
    activation: Any = None
    #: {verb -> l4_slots} for installed-skill brain verbs (ADR-0183 §am-3).
    #: Built at boot from the installed records (durable path; empty on the
    #: ephemeral path). PRE-shadow — the REPL drops any verb colliding with a
    #: builtin ``_do_*`` at construction (builtins win).
    skill_verbs: Mapping[str, Any] = field(default_factory=dict)
    #: ADR-0183 §am-4 — ``(bundle_name, reason)`` for each installed skill
    #: whose first-run Local-bootstrap importer failed at boot (unresolvable
    #: or raised). Empty on success / ephemeral path. A REPL/operator surface
    #: should report these as "reimport needed"; the next boot re-attempts
    #: (the importer self-guards on completeness).
    corpus_imports_failed: tuple = ()

    def global_view(self) -> Any:
        """The read-only bipartite probe surface over the Global L3."""
        return self.cl.global_view()

    def local_view(self) -> Any:
        """The read-only probe surface over this user's Local L3 partition."""
        return self.cl.local_view(self.user)

    def save(self) -> None:
        """Persist the user's Local to Falkor (no-op when ephemeral)."""
        if self.persister is None:
            return
        self.persister.save(self.user, self.kl.local_metagraph(self.user))


class _BrainSession:
    """Permissive single-user Local session (SessionProtocol shape).

    ``has()`` returns ``True`` for any capability — a resident brain v1 is
    single-user and only writes its OWN Local, so the ADR-0180 scope-aware
    gate (which fires on Global writes) is never tripped. Mirrors the
    Phase-49 integration ``_Session``.
    """

    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        self.session_id = f"brain-{user_id}"
        self.actor_role = "user"

    def has(self, capability: str) -> bool:  # noqa: D401 — protocol stub
        return True


def install_brain_builtins(cl: Any) -> None:
    """Install the v0 catalogs + builtins onto ``cl`` (build_stack parity)."""
    from mindsos_capacity.builtins import (
        install_orchestration_v0,
        install_phase1_v0,
        install_planning_v0,
        install_text_capacities,
        reset_v0_verdicts,
    )
    from mindsos_capacity.builtins.consolidate import install_consolidate_capacities
    from mindsos_capacity.builtins.dream import install_dream_capacities

    install_planning_v0(cl)
    install_phase1_v0(cl)
    install_orchestration_v0(cl)
    install_consolidate_capacities(cl)
    install_text_capacities(cl)
    install_dream_capacities(cl)
    reset_v0_verdicts()


def build_skill_l4_tables(records, skipped_bundles):
    """``(modality_profiles, skill_verbs, drops)`` from installed records'
    ``l4_slots`` (ADR-0183 §am-3).

    ``records`` — installed ``SkillRecordView``s, seq-ascending (install
        order == first-wins).
    ``skipped_bundles`` — bundle names in ``ActivationReport.skipped`` this
        process; their L3 capacities are absent, so binding a Phase1Profile
        against them would raise in ``phase_1.interpret`` at first use.
        Excluded here (ADR-0197 am-1 / CR D-4).

    Rules:
      * bundle in ``skipped_bundles``        → contributes nothing, reported.
      * slot dict with no ``modality``       → no verb, no profile (D-3).
      * ``modality`` already claimed (earlier seq) → first-wins, dropped +
        reported (no silent last-wins overwrite).
      * ``verb`` already claimed (earlier seq)     → first-wins, dropped +
        reported (preflight is the primary verb guard; this is defence-in-
        depth).

    Returns ``(modality_profiles, skill_verbs, drops)`` where ``drops`` is a
    list of ``(bundle_name, verb, reason)`` for anything excluded (surfaced
    by the REPL ``help``).
    """
    from mindsos_intelligence.phase1_profile import Phase1Profile

    modality_profiles: dict = {}
    skill_verbs: dict = {}
    drops: list = []
    for r in records:  # seq-ascending == install order == first-wins
        if r.bundle_name in skipped_bundles:
            drops.append(
                (r.bundle_name, None, "bundle not activated in this process")
            )
            continue
        slots = r.value.get("l4_slots") or {}
        modality = slots.get("modality")
        if not modality:
            continue  # D-3: a slot with no modality contributes nothing
        verb = slots.get("verb")
        if verb and verb in skill_verbs:
            drops.append((r.bundle_name, verb, f"verb {verb!r} already claimed"))
            continue
        if modality in modality_profiles:
            drops.append(
                (r.bundle_name, verb, f"modality {modality!r} already claimed")
            )
            continue
        modality_profiles[modality] = Phase1Profile(
            process=slots.get("process"),
            hint=slots.get("hint"),
            derive_goal=slots.get("derive_goal"),
            map=slots.get("map"),
            resolve_target_datastate=slots.get("resolve_target_datastate"),
        )
        if verb:
            skill_verbs[verb] = dict(slots)
    return modality_profiles, skill_verbs, drops


def boot_brain(
    client: Any = None,
    *,
    user: str,
    install_builtins: bool = True,
    session: Any = None,
) -> Stack:
    """Boot one resident-brain :class:`Stack`.

    Args:
        client: A live Falkor ``Client`` for the durable path, or ``None``
            for the in-memory ephemeral path. Caller owns its lifecycle.
        user: The single Local user this brain serves.
        install_builtins: Install the v0 catalogs + builtins (default).
        session: A SessionProtocol object; defaults to a permissive
            single-user :class:`_BrainSession`.
    """
    from mindsos_capacity import CapacityLayer
    from mindsos_intelligence.dispatch import L4Dispatcher
    from mindsos_intelligence.mm import MentalModel
    from mindsos_intelligence.mm_resolver import KnowledgeMMSource, MMResolver
    from mindsos_intelligence.orchestrator import Orchestrator
    from mindsos_knowledge import KnowledgeLayer

    session = session if session is not None else _BrainSession(user)
    activation: Any = None

    if client is None:
        # Ephemeral: in-memory Global, in-memory Local persister, no ledger.
        from mindsos_server.persistence.local_persister import InMemoryLocalPersister

        kl = KnowledgeLayer.bootstrap()
        cl = CapacityLayer(kl=kl)
        if install_builtins:
            install_brain_builtins(cl)
        persister: Optional[Any] = InMemoryLocalPersister()
    else:
        # Durable: load-or-mint Global from Falkor, reactivate installed skills.
        from mindsos_server.persistence.bootstrap import bootstrap_kl_from_falkordb
        from mindsos_server.persistence.local_persister import FalkorDBLocalPersister
        from mindsos_server.skills import apply_installed_skills

        kl = bootstrap_kl_from_falkordb(client)
        cl = CapacityLayer(kl=kl)
        if install_builtins:
            install_brain_builtins(cl)
        # Resilient at boot: one absent or broken bundle must not brick the
        # brain (ADR-0183 §am-2). Strict activation is the explicit
        # ``mindsos skill activate`` path, not this one. Skips are
        # process-local and reported, never written back to the record.
        activation = apply_installed_skills(cl, kl, strict=False)
        for _bundle, _reason in activation.skipped:
            log.warning(
                "boot: skill %r not activated for user %r: %s",
                _bundle,
                user,
                _reason,
            )
        persister = FalkorDBLocalPersister(client)

    # Load-or-mint the user's durable Local + reactivate its learned caps.
    from mindsos_server.local_boot import boot_local

    # Resilient: a durable Local carrying a learned descriptor whose
    # factory is not registered in this process must not brick the brain
    # (ADR-0183 §am-2 extended to reactivation). Skips are logged loudly.
    boot_local(cl, kl, persister, user, session=session, strict=False)

    # ── skill L4 bindings (ADR-0183 §am-3): the dispatcher's modality->
    #    Phase1Profile table AND the REPL's verb->slots table, built in ONE
    #    filtered pass so both share the skipped + has-modality + first-wins
    #    filter. Empty on the ephemeral path (no installed-skills graph). ──
    from mindsos_server.skills.records import latest_records_by_bundle

    installed_records = sorted(
        (
            r
            for r in latest_records_by_bundle(kl).values()
            if r.status == "installed"
        ),
        key=lambda r: r.seq,
    )
    skipped_bundles = {
        name for name, _ in (activation.skipped if activation is not None else ())
    }
    modality_profiles, skill_verbs, skill_drops = build_skill_l4_tables(
        installed_records, skipped_bundles
    )
    for _bundle, _verb, _why in skill_drops:
        log.warning(
            "boot: skill verb/profile dropped for %r (verb=%r): %s",
            _bundle,
            _verb,
            _why,
        )

    # ── first-run Local-bootstrap importers (ADR-0183 §am-4): seed a
    #    brain-owned Local corpus (e.g. a ``dataset:<name>`` graph) once, on
    #    the durable path. Best-effort like activation (§am-2): an importer
    #    that is unresolvable or raises is logged + recorded on
    #    ``Stack.corpus_imports_failed``, never bricks boot. The next boot
    #    re-attempts — the importer self-guards on completeness, so a warm
    #    Local is a cheap no-op (no corpus re-read). Called with
    #    ``(cl, kl, session)`` so it can write its own Local (the L3 ``fn(cl)``
    #    installer cannot — it has no ``kl``). ──
    corpus_imports_failed: list = []
    if client is not None:
        from mindsos_server.skills.entry_points import (
            EntryPointError,
            resolve_entry_point,
        )

        for _rec in installed_records:
            _spec = _rec.local_bootstrap_importer
            if not _spec or _rec.bundle_name in skipped_bundles:
                continue
            try:
                _fn = resolve_entry_point(_spec)
                _fn(cl, kl, session)
            except EntryPointError as _exc:
                log.warning(
                    "boot: skill %r local-bootstrap importer %r not resolvable "
                    "(%s); corpus not seeded — reimport needed.",
                    _rec.bundle_name, _spec, _exc,
                )
                corpus_imports_failed.append(
                    (_rec.bundle_name, f"unresolved: {_exc}")
                )
            except Exception as _exc:  # noqa: BLE001 — resilience contract
                log.warning(
                    "boot: skill %r local-bootstrap importer %r raised (%s: %s); "
                    "corpus may be incomplete — reimport needed.",
                    _rec.bundle_name, _spec, _exc.__class__.__name__, _exc,
                )
                corpus_imports_failed.append(
                    (_rec.bundle_name, f"import-failed: {_exc}")
                )

    mm = MentalModel(session_id=session.session_id, user_id=user)
    # ADR-0200 (Slice 3): the solve-path dispatcher's read-only MM handle is
    # the concrete ``MMResolver`` (KL-backed source), gated on ``reads_mm``.
    # Inert until a ``reads_mm=True`` consumer ships. The Orchestrator's write
    # access is the real ``mm`` passed below, not this read handle.
    dispatcher = L4Dispatcher(
        cl,
        session=session,
        kl=kl,
        mm_handle=MMResolver(mm, KnowledgeMMSource(kl)),
        modality_profiles=modality_profiles,
    )
    # DQ-8 / CR#4 — persist per-task chain graphs so an Episode's mm_root_ref
    # resolves. Durable path only; the ephemeral path (client is None) stays
    # live-only.
    mm_persister = None
    if client is not None:
        from mindsos_intelligence.mm_persister import FalkorMMPersister

        mm_persister = FalkorMMPersister(client)
    # Dream PRE-0 Slice 1b (D3) — give the Orchestrator the durable Local
    # persister so the streaming Episode's open / suspend / close each flush the
    # Local to Falkor (crash durability). Durable path only; the ephemeral
    # in-memory persister is left unwired here (nothing to make durable).
    local_persister = persister if client is not None else None
    orch = Orchestrator(
        dispatcher,
        mm,
        request_scope="brain",
        mm_persister=mm_persister,
        local_persister=local_persister,
    )
    # Dream PRE-0 Slice 1b — recover crashed Episodes from a prior session at
    # boot: scan the user's Local for ``state=open`` Episodes (a crash before the
    # terminal close) and stamp each closed + ``outcome=failed``. Durable path
    # only; a fresh in-memory Local has nothing to recover. Best-effort — a
    # recovery failure must not brick the brain (ADR-0183 §am-2 posture).
    if client is not None:
        from mindsos_intelligence import crash_recovery

        try:
            crash_recovery.recover_unconsolidated(
                dispatcher, local_persister=persister
            )
        except Exception as exc:  # noqa: BLE001 — boot resilience
            log.warning("boot: crash recovery scan failed for %r: %s", user, exc)
    return Stack(
        kl, cl, mm, dispatcher, orch, session, persister, user,
        activation=activation,
        skill_verbs=skill_verbs,
        corpus_imports_failed=tuple(corpus_imports_failed),
    )


__all__ = [
    "Stack",
    "boot_brain",
    "install_brain_builtins",
    "build_skill_l4_tables",
]
