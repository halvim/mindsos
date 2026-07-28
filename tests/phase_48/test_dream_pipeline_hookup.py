"""Phase 48 S5 — dream-cycle driver invokes the 3 Phase-45 dream capacities
and emits directives with ``source_episode_iri`` provenance; ``dream.retry``
fires only on failed episodes with a ReplanInjectionDirective (ADR-0178;
Chat B §5.2). Faithful re-execution + ALS firing are WSD-gated (PB-9) — the
re-exec hook is exercised here."""

from mindsos_capacity import CapacityLayer
from mindsos_capacity.builtins.dream import install_dream_capacities
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_intelligence.dream_cycle import (
    DreamDriver,
    dream_task_ref,
    invoke_dream_capacities,
    run_dream_cycle,
)
from mindsos_knowledge import KnowledgeLayer


def _dispatcher():
    layer = CapacityLayer(kl=KnowledgeLayer.bootstrap())
    install_dream_capacities(layer)

    class _S:
        session_id = "s"
        user_id = "u"

        def has(self, c):
            return True

    return L4Dispatcher(layer, session=_S(), kl=layer._kl)


def test_non_failed_episode_emits_maintenance_and_exploration_only():
    d = _dispatcher()
    directives = invoke_dream_capacities(
        d, dream_task_ref(source_episode_iri="ep:1", request_run_iri="tr:1", failed=False)
    )
    policies = sorted(x.execution_policy for x in directives)
    assert policies == ["re_execute_capacities", "replay_recorded"]  # exploration + maintenance
    assert all(x.source_episode_iri == "ep:1" for x in directives)
    assert all(x.replan_injection is None for x in directives)


def test_failed_episode_emits_retry_with_replan_injection():
    d = _dispatcher()
    directives = invoke_dream_capacities(
        d, dream_task_ref(source_episode_iri="ep:2", request_run_iri="tr:2", failed=True)
    )
    # maintenance + exploration + retry all fire on a failed episode
    assert len(directives) == 3
    with_injection = [x for x in directives if x.replan_injection is not None]
    assert len(with_injection) == 1
    inj = with_injection[0].replan_injection
    assert inj.source_episode_iri == "ep:2"
    assert inj.replan_level == "taskrun"


def test_run_dream_cycle_over_corpus_calls_re_executor_per_directive():
    d = _dispatcher()
    seen = []
    episodes = [
        {"source_episode_iri": "ep:1", "task_run_iri": "tr:1", "failed": False},
        {"source_episode_iri": "ep:2", "task_run_iri": "tr:2", "failed": True},
    ]
    directives = run_dream_cycle(d, episodes, re_executor=seen.append)
    # ep:1 -> 2 directives; ep:2 -> 3 directives
    assert len(directives) == 5
    assert len(seen) == 5
    assert {x.source_episode_iri for x in directives} == {"ep:1", "ep:2"}


def test_dream_driver_pulls_corpus_and_runs():
    d = _dispatcher()
    corpus = [{"source_episode_iri": "ep:9", "failed": False}]
    driver = DreamDriver(d, lambda: corpus)
    directives = driver()
    assert {x.source_episode_iri for x in directives} == {"ep:9"}
