"""dr_mutations — every new guard, shown RED by a named mutation, then reverted.

**Why this is an instrument and not eleven hand-runs.** RULES §12.2 requires
one mutation per new guard and calls *a mutation that reddens nothing* a
finding. Done by hand that is eleven edit/run/revert cycles, each an
opportunity to leave the tree mutated or to re-run a stale `.pyc` — the two
traps this lane has already recorded. Done here it is one command whose output
is a table, and the revert is a `finally`.

**It is not demo content.** It renders nothing, it registers nothing, and the
room never sees it. It is ship discipline, in the same category as
`dr_dump.py`.

**What it does, precisely.** For each mutation: apply an exact string
replacement to a source file, run every guard file in a FRESH SUBPROCESS
(`PYTHONDONTWRITEBYTECODE=1`, so a same-length revert cannot leave a mutated
`.pyc` behind), record which tests went red, then restore the file byte for
byte. Every source is hashed before and after the whole run and the hashes are
printed — if the tree is not identical at the end, that is the first thing you
see.

**Read the output as a prediction test, not a pass list.** Each row carries the
tests the build lane predicted would redden. A mutation whose actual red set is
EMPTY means the guard cannot fail and is worse than no guard. A mutation whose
actual set differs from the predicted one is a finding about the prediction,
which is usually a finding about the code.

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 decision_records_demo/dr_mutations.py
"""

from __future__ import annotations

import hashlib
import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

RENDER = "decision_records_demo/dr_render.py"
SCREEN = "decision_records_demo/dr_screen.py"
SETTLE = "decision_records_demo/dr_settlement.py"
ROUTING = "decision_records_demo/dr_routing.py"
BEAT = "decision_records_demo/dr_demo_beat.py"
ASSESS = "decision_records_demo/dr_assessment.py"
PAGES = "decision_records_demo/dr_render_pages.py"
TRANSPORT = "decision_records_demo/dr_transport.py"

GUARD_FILES = (
    "decision_records_demo/test_dr_render_guards.py",
    "decision_records_demo/test_dr_routing_guards.py",
    "decision_records_demo/test_dr_screen_guards.py",
    # Added by ship B slice 2, which mutates the beat runner. These guards
    # render NO page (no store, no docker), so no existing row's red set
    # should move; that prediction is the reason to say it here rather than
    # to notice it afterwards.
    "decision_records_demo/test_dr_beat_guards.py",
    "decision_records_demo/test_dr_assessment_guards.py",
    # Added by step 1, which mutates the transport. These guards import
    # ONLY dr_transport — no store, no renderer, no docker — so the
    # prediction that comes with them is that NO existing row's red set
    # moves. Said here rather than noticed on the first run.
    "decision_records_demo/test_dr_transport_guards.py",
)

#: ⚠ **THE ECHO RULE COUPLED TWO REGIONS OF THE PAGE (ship B).** The intake
#: line now drops values that appear in the deciding QUESTION or the VERDICT
#: sentence, so a mutation that changes either of those changes the intake
#: line as well. Eight predictions written before that coupling existed were
#: wrong in the same direction on the first run after it landed — they are
#: widened below, each because the mutation genuinely disturbs a second
#: region, not because the output was copied back.
#: (name, file, old, new, predicted-red test names)
MUTATIONS = [
    (
        "the intake line echoes the deciding fact again",
        RENDER,
        # ⚠ RE-ANCHORED in ship B: the comprehension gained the two text
        # doors, so the one-line form this row pointed at stopped existing.
        # Caught as DEAD before the run rather than by a shorter table.
        "        if v != drop\n"
        "        and not any(_token_in(str(v), text) for text in texts if text)",
        "        if True",
        [
            "test_the_intake_line_does_not_echo_the_VERDICT_SENTENCE",
            "test_the_intake_line_does_not_echo_the_deciding_QUESTION",
            "test_the_intake_line_does_not_echo_the_deciding_fact",
        ],
    ),
    (
        "a NON-DICT verdict is punished for naming no deciding fact",
        RENDER,
        "        if not isinstance(verdict, dict):\n            return None",
        '        if not isinstance(verdict, dict):\n            raise RendererGapError("not a dict")',
        # The SECOND door out of deciding_lines, and the one the asymmetry
        # guard used to test by accident instead of on purpose.
        # Every fixture whose verdict is NOT a dict: the policy leaf's bare
        # limit and the bare-verdict correlation pair. The policy-version
        # guard is here too, and only because it was tightened to assert its
        # own message — before that it caught this unrelated raise and stayed
        # green, which is how the harness found it.
        [
            "test_a_capacity_that_records_no_deciding_fact_is_not_punished",
            "test_a_missing_supplied_policy_version_raises",
            "test_g5_two_dates_name_different_limits_and_windows",
            "test_identical_bare_verdicts_do_not_collapse_onto_one_member",
            "test_identical_bare_verdicts_render_by_position",
        ],
    ),
    (
        "deciding_lines returns [] instead of raising on an unfindable pair",
        RENDER,
        "        if answer_node is None or record_node is None:\n",
        "        if answer_node is None or record_node is None:\n            return []\n",
        ["test_a_declared_deciding_fact_with_no_stored_question_raises"],
    ),
    (
        "the producing-capacity cross-check is removed (name match alone)",
        RENDER,
        "        if answer_by is None or answer_by != record_by:",
        "        if False:",
        ["test_a_question_and_an_answer_from_different_capacities_raise"],
    ),
    (
        "a refusing record is accepted as a deciding fact",
        RENDER,
        "        if not isinstance(record, dict) or not record.get(FIELD_ADMITTED):",
        "        if False:",
        ["test_a_verdict_standing_on_a_refusing_record_raises"],
    ),
    (
        "the member block stops emitting the deciding fact",
        RENDER,
        "    lines.extend(member.deciding_lines(entry))\n",
        "",
        [
            "test_only_the_deciding_read_reaches_the_page",
            "test_case_a_one_claim_two_desks",
            "test_case_b_refusal_beside_answers_names_the_item",
            "test_the_deciding_fact_and_the_refusal_do_not_share_a_style",
            "test_the_intake_line_does_not_echo_the_deciding_fact",
        ],
    ),
    (
        # ⚠ A KNOWN, EXPLAINED PREDICTION MISS, and it is left that way on
        # purpose. The marker's VALUE is ``datastate:...`` and ``datastate:``
        # is itself in ``G6_BANNED``, so render-time G6 raises before the
        # named guard can assert anything: EVERY guard that renders a page
        # carrying a deciding fact goes red, in all three guard files. The
        # prediction names the guard that OWNS the claim, because that is the
        # useful sentence; the harness cannot express "and every guard that
        # renders this page". The set grew again in ship B slice 1 when three
        # page-rendering guards were added, and it will grow again. Filed as
        # the instrument gap rather than maintained by hand.
        "the determining marker is printed on the page",
        RENDER,
        # ⚠ RETARGETED in ship B. `deciding_fact` was split so the deciding
        # fact's SOURCE could reuse its pairing, and `marker` left that
        # scope — the anchor stayed ALIVE while its meaning moved, so the
        # mutation would have raised NameError and reddened by accident
        # instead of by printing the marker. The harness detects DEAD
        # anchors, not DISPLACED ones; this is the second failure mode and
        # it is quieter.
        '        return [f"   Q. {question} — {_fmt(answer)}."]',
        '        return [f"   Q. {verdict.get(FIELD_DETERMINED_BY)} {question} — {_fmt(answer)}."]',
        ["test_the_determining_marker_never_reaches_the_page"],
    ),
    (
        "a verdict with NO determining input is punished instead of rendered",
        RENDER,
        "        if not marker:\n            return None",
        '        if not marker:\n            raise RendererGapError("no determining input")',
        # EVERY fixture whose verdicts are dicts without the field — the
        # decide/conclude family and the partial/noroute/boundary shapes built
        # on it — plus the screen tests that compose those pages. The wide set
        # is the point: this branch is load-bearing for every page that
        # predates the deciding fact.
        [
            "test_a_capacity_that_records_no_deciding_fact_is_not_punished",
            "test_a_from_root_page_differs_in_exactly_the_date_line",
            "test_a_genuinely_duplicated_exposure_still_renders",
            "test_a_screen_without_intake_omits_the_panel",
            "test_fact_channel_equals_the_page_on_every_known_form",
            "test_manifest_naming_a_missing_graph_raises",
            "test_manifest_only_member_renders_no_route_block",
            "test_missing_decided_date_is_stated_not_omitted",
            "test_old_reds_stay_red_on_the_no_manifest_road",
            "test_order_follows_the_record_alone",
            "test_page_renders_and_is_g6_clean",
            "test_partial_page_stop_block_in_place",
            "test_refusal_stop_and_therefore_classify_as_themselves",
            "test_stop_graph_with_produced_verdict_is_incoherent",
            "test_unmatched_member_graph_raises",
        ],
    ),
    (
        "the conclusion is picked by iteration order again",
        RENDER,
        "        out = self._unconsumed(self.plain_produced())",
        "        out = self.plain_produced()[:1]",
        [
            "test_beat4_page_carries_a_decision_not_two_lookups",
            "test_over_the_limit_the_limit_is_the_deciding_fact",
            "test_the_deciding_fact_carries_the_authority_behind_it",
            "test_the_leaf_road_shows_the_deciding_fact",
            "test_the_two_dates_pay_different_amounts_and_name_their_editions",
            "test_two_unconsumed_values_raise_rather_than_pick_one",
            "test_under_the_limit_the_amount_is_the_deciding_fact",
            "test_a_short_intake_value_survives_when_it_only_LOOKS_echoed",
            "test_the_intake_line_does_not_echo_the_VERDICT_SENTENCE",
            "test_the_intake_line_does_not_echo_the_deciding_QUESTION",
        ],
    ),
    (
        "the completed check asks plain_produced again (a refusal stops counting)",
        RENDER,
        "not terminal.terminal_outcomes():",
        "not terminal.plain_produced():",
        ["test_a_refusing_leaf_is_a_conclusion_not_a_missing_one"],
    ),
    (
        "the leaf verdict line wears the first capacity's phrase again",
        RENDER,
        'f"   {analysis.phrase_for_value(produced[0].value)} → "',
        'f"   {analysis.phrase()} → "',
        [
            "test_beat4_page_carries_a_decision_not_two_lookups",
            "test_the_leaf_road_shows_the_deciding_fact",
        ],
    ),
    (
        "every Q line classifies as a refusal on the screen",
        SCREEN,
        'return "refusal" if line.startswith("Q. ") else "reason"',
        'return "refusal"',
        ["test_the_deciding_fact_and_the_refusal_do_not_share_a_style"],
    ),
    (
        "dr_settlement spells the determining field differently",
        SETTLE,
        'DETERMINED_BY = "determined_by"',
        'DETERMINED_BY = "determined"',
        [
            "test_the_field_name_is_spelled_the_same_in_all_three_places",
            "test_the_leaf_road_shows_the_deciding_fact",
        ],
    ),
    (
        "the claim line COUNTS the pending exposures instead of naming them",
        ROUTING,
        """        parts.append(f"{len(pending)} not yet assigned: {'; '.join(pending)}")""",
        """        parts.append(f"{len(pending)} cannot be assigned yet - see the exposure above")""",
        [
            "test_case_b_refusal_beside_answers_names_the_item",
            "test_the_claim_line_names_the_pending_exposure",
            "test_the_member_road_does_not_gain_the_refusal_verdict_line",
        ],
    ),
    (
        "the exposure name rides on REFUSALS only - ship A's one-member shape",
        ROUTING,
        "        if ref:\n            fields[EXPOSURE_REF] = ref",
        '        if ref and fields.get("decision") is None:\n'
        "            fields[EXPOSURE_REF] = ref",
        ["test_every_desk_verdict_names_its_exposure_answered_and_refused"],
    ),
    (
        "the pluraliser is hardcoded plural - '1 exposures', in the room",
        ROUTING,
        """            f"{routine} exposure{'' if routine == 1 else 's'} to {ROUTINE_DESK}\"""",
        '            f"{routine} exposures to {ROUTINE_DESK}"',
        # The direct-call door of the raise guard reads the same line, so it
        # reddens here too; predicted rather than discovered.
        [
            "test_the_claim_line_is_singular_at_one_and_plural_at_two",
            "test_a_refusing_verdict_with_no_exposure_name_raises",
        ],
    ),
    (
        # The FIRST version of this row emitted ``str(verdict)``, whose repr
        # carries ``refusal_reason`` and ``field_absent`` — both G6-banned —
        # so render-time G6 raised and it reddened four screen guards on top
        # of the three named. That was a bad MUTATION, not a bad prediction:
        # the claim is "the field NAME never reaches the page", so the
        # mutation is the smallest edit that makes exactly that false.
        "the pending name is emitted as the FIELD NAME instead of the words",
        ROUTING,
        "        pending.append(ref)",
        "        pending.append(EXPOSURE_REF)",
        [
            "test_case_b_refusal_beside_answers_names_the_item",
            "test_the_claim_line_names_the_pending_exposure",
            "test_the_exposure_field_name_never_reaches_the_page",
            "test_the_member_road_does_not_gain_the_refusal_verdict_line",
        ],
    ),
    (
        "an unnameable refusal is FILLED with a placeholder instead of raising",
        ROUTING,
        '            raise ValueError(\n'
        '                "a desk verdict refused without naming its exposure - "\n'
        '                "refusing to publish a count where the page needs a name"\n'
        "            )",
        '            ref = "an exposure above"',
        ["test_a_refusing_verdict_with_no_exposure_name_raises"],
    ),
    (
        "the closer prefers the WEAKEST page again - the walk gap 5 defect",
        BEAT,
        'CLOSER_PREFERENCE = ("routingrefusal", "routing", "settlement")',
        'CLOSER_PREFERENCE = ("settlement", "routing", "routingrefusal")',
        [
            "test_the_closer_rebuilds_the_richest_record_the_room_watched",
            "test_the_closer_refuses_when_no_beat_has_run",
        ],
    ),
    (
        "a preferred case NO BEAT RUNS is accepted, and silently demotes",
        BEAT,
        'CLOSER_PREFERENCE = ("routingrefusal"',
        'CLOSER_PREFERENCE = ("routing_refusal"',
        [
            "test_every_closer_preference_is_a_case_a_beat_actually_runs",
            "test_the_closer_rebuilds_the_richest_record_the_room_watched",
        ],
    ),
    (
        "the assessment loses its registered phrase",
        ASSESS,
        'printable_phrase="assessing the claimed amount against the limit in force"',
        'printable_phrase="looking the limit up"',
        [
            # The refusal guard asserts the whole verdict line, phrase
            # included, since the cannot-phrase contract landed.
            "test_a_claim_with_no_amount_refuses_in_the_readers_words",
            "test_beat4_page_carries_a_decision_not_two_lookups",
        ],
    ),
    (
        "beat 4's two cases collapse onto ONE date",
        ASSESS,
        'CASE_ASSESSED_CURRENT = dict(CASE_ASSESSED_PRIOR, assessed_as_of="2024-06-01")',
        "CASE_ASSESSED_CURRENT = dict(CASE_ASSESSED_PRIOR)",
        ["test_the_two_dates_pay_different_amounts_and_name_their_editions"],
    ),
    (
        "over the limit, the page credits the AMOUNT for capping the payment",
        ASSESS,
        "            DETERMINED_BY: DS_DWELLING_LIMIT,",
        "            DETERMINED_BY: DS_CLAIMED_AMOUNT,",
        [
            "test_over_the_limit_the_limit_is_the_deciding_fact",
            "test_the_deciding_fact_carries_the_authority_behind_it",
            "test_the_two_dates_pay_different_amounts_and_name_their_editions",
            "test_what_is_payable_is_arithmetic_on_the_stored_values",
            "test_the_intake_line_does_not_echo_the_deciding_QUESTION",
        ],
    ),
    (
        "under the limit, the page credits the LIMIT - the two-door other side",
        ASSESS,
        "        DETERMINED_BY: DS_CLAIMED_AMOUNT,",
        "        DETERMINED_BY: DS_DWELLING_LIMIT,",
        [
            "test_under_the_limit_the_amount_is_the_deciding_fact",
            "test_what_is_payable_is_arithmetic_on_the_stored_values",
        ],
    ),
    (
        "a claim with no amount is DECIDED on instead of refused",
        ASSESS,
        "    if claimed is None or limit is None:",
        "    if limit is None:",
        ["test_a_claim_with_no_amount_refuses_in_the_readers_words"],
    ),
    (
        "the subtraction is inverted - the room's arithmetic stops matching",
        ASSESS,
        "{claimed - limit} above the limit",
        "{limit - claimed} above the limit",
        [
            "test_beat4_page_carries_a_decision_not_two_lookups",
            "test_the_two_dates_pay_different_amounts_and_name_their_editions",
            "test_what_is_payable_is_arithmetic_on_the_stored_values",
        ],
    ),
    (
        "the as-of date is read under a question the store cannot show",
        ASSESS,
        'question="As of what date is this claim being considered?"',
        'question="Which date applies?"',
        ["test_the_as_of_date_is_a_read_fact_with_its_own_stored_question"],
    ),
    (
        "both beat-4 pages frame themselves as the ASSESSMENT again",
        PAGES,
        '"claim CLM-4188, as submitted on 2023-06-01",',
        '"claim CLM-4188, assessed as of 2023-06-01",',
        ["test_the_two_pages_carry_the_SUBMISSION_and_ASSESSMENT_framing"],
    ),
    (
        "the deciding fact loses the authority behind it",
        RENDER,
        "        if record.get(FIELD_PRODUCER_KIND) != PRODUCER_POLICY_LOOKUP:\n            return []",
        "        if True:\n            return []",
        [
            "test_the_deciding_fact_carries_the_authority_behind_it",
            "test_the_two_dates_pay_different_amounts_and_name_their_editions",
        ],
    ),
    (
        "the payable numbers are formatted with an invented separator",
        ASSESS,
        'f"{claimed} claimed, {limit} payable, "',
        'f"{claimed:,} claimed, {limit:,} payable, "',
        [
            "test_beat4_page_carries_a_decision_not_two_lookups",
            "test_no_invented_currency_reaches_the_page",
            "test_the_two_dates_pay_different_amounts_and_name_their_editions",
            "test_what_is_payable_is_arithmetic_on_the_stored_values",
            "test_the_intake_line_does_not_echo_the_VERDICT_SENTENCE",
        ],
    ),
    (
        "a refusing leaf hides the decision it could not make",
        RENDER,
        "            carriers = analysis.refusing_conclusions()",
        "            carriers = []",
        [
            # The mutation stops `refusing_conclusions()` being CALLED, so its
            # two-carrier raise never fires either: the two guards share one
            # call site.
            "test_a_refusing_leaf_names_the_decision_it_could_not_make",
            "test_two_unconsumed_refusal_carriers_raise_rather_than_pick_one",
            "test_a_claim_with_no_amount_refuses_in_the_readers_words",
            "test_a_refusing_leaf_with_no_words_of_its_own_raises",
        ],
    ),
    (
        "the refusal verdict line LEAKS onto the member road",
        RENDER,
        # ⚠ The first anchor was the three lines `lines.extend(block)` /
        # `lines.append("")` / `continue`, which occur TWICE — the member
        # refusal block and the no-route block. `.replace(old, new, 1)` took
        # the earlier one, so the mutation edited a path this row never meant:
        # it reddened `test_manifest_only_member_renders_no_route_block` while
        # the guard it exists for stayed green. The harness now refuses an
        # ambiguous anchor outright.
        """                block.append(
                    f"Q. {record.get('question')} — Nothing. "
                    f"{record.get('refusal_detail')}"
                )
                lines.extend(block)""",
        """                block.append(
                    f"Q. {record.get('question')} — Nothing. "
                    f"{record.get('refusal_detail')}"
                )
                block.append(f"   {member.phrase_for_value(entry)} → placed")
                lines.extend(block)""",
        ["test_the_member_road_does_not_gain_the_refusal_verdict_line"],
    ),
    (
        "two unconsumed refusal carriers are picked from by iteration order",
        RENDER,
        "        if len(out) > 1:\n            raise RendererGapError(\n                f\"{self.graph.role!r} produced more than one refusing value \"",
        "        if False:\n            raise RendererGapError(\n                f\"{self.graph.role!r} produced more than one refusing value \"",
        ["test_two_unconsumed_refusal_carriers_raise_rather_than_pick_one"],
    ),
    (
        "the refusing leaf's own words go missing",
        SETTLE,
        'CANNOT_SETTLE = "cannot be settled"',
        'CANNOT_SETTLE = ""',
        [
            # An EMPTY phrase is not a MISSING one: the field is still there
            # and falsy, so the strip-fixture finds nothing and its
            # `stripped == 1` drift assertion fires. That is the fixture
            # refusing to pass on a premise that stopped being true.
            "test_a_refusing_leaf_is_a_conclusion_not_a_missing_one",
            "test_a_refusing_leaf_names_the_decision_it_could_not_make",
            "test_a_refusing_leaf_with_no_words_of_its_own_raises",
            "test_beat3_missing_document_names_what_to_fetch",
        ],
    ),
    (
        "the ASSESSMENT loses its own words - the contract's second member",
        ASSESS,
        'CANNOT_ASSESS = "cannot be assessed"',
        'CANNOT_ASSESS = ""',
        ["test_a_claim_with_no_amount_refuses_in_the_readers_words"],
    ),
    (
        "the renderer COMPOSES for the capacity again instead of raising",
        RENDER,
        "                if not said:",
        "                if False:",
        [
            # ⚠ ONE name, not three. `if False:` only reaches the path where a
            # phrase is MISSING; every shipped producer supplies one, so the
            # line renders normally and only the strip-fixture guard notices.
            # The first prediction assumed a mutation broke a path it does
            # not touch.
            "test_a_refusing_leaf_with_no_words_of_its_own_raises",
        ],
    ),
    (
        "the refusal-phrase field is spelled differently by its producer",
        SETTLE,
        'REFUSAL_PHRASE = "refusal_phrase"',
        'REFUSAL_PHRASE = "refusal_phrase_x"',
        [
            "test_a_refusing_leaf_names_the_decision_it_could_not_make",
            "test_the_field_name_is_spelled_the_same_in_all_three_places",
            "test_a_refusing_leaf_is_a_conclusion_not_a_missing_one",
            "test_a_refusing_leaf_with_no_words_of_its_own_raises",
            "test_beat3_missing_document_names_what_to_fetch",
        ],
    ),
    (
        "the echo rule loses its SECOND door - the deciding question",
        RENDER,
        "                    _leaf_texts.append(str(_leaf_fact[0]))",
        "                    pass",
        ["test_the_intake_line_does_not_echo_the_deciding_QUESTION"],
    ),
    (
        "the echo rule loses its THIRD door - the verdict sentence",
        RENDER,
        "                _leaf_texts.append(_verdict_text(_leaf_produced[0].value))",
        "                pass",
        ["test_the_intake_line_does_not_echo_the_VERDICT_SENTENCE"],
    ),
    (
        "the echo match relaxes to a bare substring - 50 inside 50000",
        RENDER,
        "        if not before.isalnum() and not after.isalnum():",
        "        if True:",
        ["test_a_short_intake_value_survives_when_it_only_LOOKS_echoed"],
    ),
    (
        "the unfindable-pair raise stops saying which gap it is",
        RENDER,
        'f"it, but {missing} is not in this run\'s stored evidence — "',
        'f"it, but {missing} is unavailable — "',
        ["test_a_declared_deciding_fact_with_no_stored_question_raises"],
    ),
    # ── STEP 1 — the transport. Seven rows, one per new guard.
    # Every anchor is in dr_transport.py, which NO other guard file imports,
    # so each predicted red set is exactly one test. That is a claim in BOTH
    # directions (RULES §12): not only "these reddens", but "nothing in
    # render, routing, screen, assessment or beat is touched by any of them".
    (
        "a transport parameter carries a default, so a caller can omit the document",
        TRANSPORT,
        "        source_text: str,",
        '        source_text: str = "",',
        ["test_the_callable_binds_the_call_LiveLLM_makes_and_requires_all_five"],
    ),
    (
        "the transport DECODES the model's answer instead of returning text (S-2)",
        TRANSPORT,
        '        return "".join(parts)',
        '        return json.loads("".join(parts))',
        # Guard 4's first assertion survives: `KEY not in <dict>` tests keys.
        ["test_a_successful_call_returns_the_models_text_undecoded"],
    ),
    (
        "a non-2xx is treated as an answer instead of a failure",
        TRANSPORT,
        "        if not 200 <= int(status) < 300:",
        "        if False:",
        ["test_a_non_2xx_raises_as_an_OUTAGE_and_returns_nothing"],
    ),
    (
        "the credential is appended to the outage message",
        TRANSPORT,
        "            raise TransportCallFailed(UNREACHABLE) from exc",
        '            raise TransportCallFailed(UNREACHABLE + " " + api_key) from exc',
        # NOT guard 5 as well: the test key contains "ant" and not
        # "anthropic", and carries neither the model id nor the endpoint.
        ["test_the_api_key_reaches_no_return_value_and_no_exception_in_the_chain"],
    ),
    (
        "the model id is appended to the outage message",
        TRANSPORT,
        "            raise TransportCallFailed(UNREACHABLE) from exc",
        '            raise TransportCallFailed(UNREACHABLE + " " + model_id) from exc',
        ["test_the_model_id_and_endpoint_reach_no_exception_this_module_raises"],
    ),
    (
        "the per-call timeout is dropped and the opener's default is used",
        TRANSPORT,
        "            response = open_url(request, timeout=timeout_s)",
        "            response = open_url(request)",
        ["test_the_timeout_reaches_the_opener"],
    ),
    (
        "a prompt is inlined in the module instead of coming from the resolver",
        TRANSPORT,
        "        system = resolve_prompt(prompt_iri=prompt_iri, prompt_version=prompt_version)",
        '        system = "read the message and report what it states"',
        ["test_the_prompt_comes_from_the_injected_resolver"],
    ),
]

_RUNNER = (
    "import importlib.util,sys,traceback\n"
    "spec=importlib.util.spec_from_file_location('m',sys.argv[1])\n"
    "m=importlib.util.module_from_spec(spec)\n"
    "try:\n"
    "    spec.loader.exec_module(m)\n"
    "except Exception:\n"
    "    print('IMPORT-RED'); raise SystemExit(0)\n"
    "for name in sorted(n for n in dir(m) if n.startswith('test_')):\n"
    "    try:\n"
    "        getattr(m,name)()\n"
    "    except Exception:\n"
    "        print('RED '+name)\n"
)


def _hash(path: str) -> str:
    with open(os.path.join(ROOT, path), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:12]


def _red_set() -> set:
    red = set()
    for guard_file in GUARD_FILES:
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=ROOT)
        out = subprocess.run(
            [sys.executable, "-c", _RUNNER, os.path.join(ROOT, guard_file)],
            cwd=ROOT, env=env, capture_output=True, text=True,
        ).stdout
        for line in out.splitlines():
            if line.startswith("RED "):
                red.add(line[4:].strip())
            elif line == "IMPORT-RED":
                red.add("<" + os.path.basename(guard_file) + " did not import>")
    return red


def _declared_test_names() -> set:
    """Every test name the guard files define, by source scan.

    **Why this exists, and it is the harness auditing its own input.** On
    2026-08-17 three rows had two test names spliced into ONE by an editing
    slip — Python concatenates adjacent string literals silently, so
    ``["test_a"  "test_b"]`` is the single name ``"test_atest_b"``, which no
    run can ever produce. All three printed as PREDICTION MISS and looked
    like findings about the CODE. A prediction naming a test that does not
    exist is a finding about the PREDICTION, and it is now caught before a
    single mutation is applied.
    """
    names = set()
    for guard_file in GUARD_FILES:
        with io.open(os.path.join(ROOT, guard_file), encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("def test_"):
                    names.add(line[4:].split("(")[0].strip())
    return names


def main() -> int:
    declared = _declared_test_names()
    phantom = sorted(
        (name, row[0]) for row in MUTATIONS for name in row[4]
        if name not in declared
    )
    ambiguous = []
    for name, path, old_text, _new, _pred in MUTATIONS:
        body = io.open(os.path.join(ROOT, path), encoding="utf-8").read()
        if body.count(old_text) > 1:
            ambiguous.append((name, path, body.count(old_text)))
    if ambiguous:
        print("== anchors that occur more than once ==")
        for name, path, count in ambiguous:
            print("  %s  (%s, %d occurrences)" % (name, path, count))
        print("  `.replace(old, new, 1)` picks the FIRST, so the mutation "
              "edits a site the row may not mean — it reddens the wrong guard "
              "and the right one stays green. Narrow the anchor.")
        return 5
    if phantom:
        print("== predictions naming tests that do not exist ==")
        for name, row in phantom:
            print("  %r  (row: %s)" % (name, row))
        print("  A prediction no run can satisfy is not a prediction. Fix "
              "these before reading anything below.")
        return 5
    before = {f: _hash(f) for f in (RENDER, SCREEN, SETTLE, ROUTING, BEAT, ASSESS, PAGES, TRANSPORT)}
    print("== baseline: every guard file green with no mutation applied ==")
    baseline = _red_set()
    if baseline:
        print("BASELINE IS NOT GREEN — everything below is meaningless:")
        for name in sorted(baseline):
            print("  RED " + name)
        return 2
    print("baseline green\n")

    findings = 0
    dead = 0
    for name, path, old, new, predicted in MUTATIONS:
        full = os.path.join(ROOT, path)
        original = io.open(full, encoding="utf-8").read()
        if old not in original:
            # A DEAD MUTATION IS THE WORST OUTCOME THIS FILE HAS, and it is
            # not a row in a table. It means a guard's only proof of failure
            # silently stopped existing — which happened on the first refactor
            # after this harness was written (``deciding_lines`` split into
            # ``deciding_fact``, 2026-08-17, three anchors dead at once). A
            # dead mutation reports NOTHING and reads like a shorter run.
            print("== %s ==\n  ⚠ MUTATION DID NOT APPLY — its anchor is not in %s.\n"
                  "     The guard it proves has no proof. Fix the anchor before "
                  "reading anything else here." % (name, path))
            dead += 1
            continue
        try:
            io.open(full, "w", encoding="utf-8").write(original.replace(old, new, 1))
            actual = _red_set()
        finally:
            io.open(full, "w", encoding="utf-8").write(original)
        print("== %s ==" % name)
        print("  file      : %s" % path)
        print("  predicted : %s" % ", ".join(sorted(predicted)))
        print("  actual    : %s" % (", ".join(sorted(actual)) or "NOTHING"))
        if not actual:
            print("  ⚠ FINDING: this mutation reddens nothing — the guard cannot fail")
            findings += 1
        elif set(predicted) != actual:
            print("  ⚠ PREDICTION MISS: the difference is the finding")
            findings += 1
        else:
            print("  exact")
        print()

    after = {f: _hash(f) for f in (RENDER, SCREEN, SETTLE, ROUTING, BEAT, ASSESS, PAGES, TRANSPORT)}
    print("== tree restored ==")
    for f in sorted(before):
        mark = "OK " if before[f] == after[f] else "⚠ NOT RESTORED "
        print("  %s%s  %s -> %s" % (mark, f, before[f], after[f]))
    if before != after:
        return 3
    print("\n== re-verify: the guards are green again after every revert ==")
    residue = _red_set()
    print("red after revert: %s" % (", ".join(sorted(residue)) or "none"))
    if residue:
        return 3
    print("\nmutations: %d, findings: %d, DEAD: %d" % (len(MUTATIONS), findings, dead))
    return 4 if dead else 0


if __name__ == "__main__":
    raise SystemExit(main())
