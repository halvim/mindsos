# ADR-0183 §amendment-5 — DRAFT (proposed)

Insertion into `docs/decisions/adr/0183-skill-bundle-install-lifecycle.md` after
`## Amendment §am-4`. Implemented on `feat/skill-local-caps`; pairs with
**ADR-0150 §Revisions** (new Local role `installed-capacities`). Cites shipped
`file:line`.

---

## Amendment §am-5 — installed skills as apps: lazily-loaded Local capabilities

**Context.** A skill bundle could register capacities only into **Global** L3
(`apply_installed_skills` → `fn(cl)`, Global). It could not contribute durable,
per-user **Local** capabilities that behave like installed applications:
installed once, present at every boot, their program started on use. Two facts
make this expressible cleanly: a capability's function field is optional
(`capacity.py:73`, `implementation: Optional = None`; validated only when
present), and the planner selects capabilities from graph **metadata**, not the
function (the function is touched only at `invoke`).

**Decision — separate an app's *data* from its *behavior*.**

* **Declaration (data).** A bundle declares each Local capability in its manifest
  as a `[[l3.local_capacity]]` entry — `name`, `category`, `inputs`, `outputs`,
  a `reactivation_key` naming the builder, and opaque `params`
  (`manifest.py`: `LocalCapabilityEntry` + parse). Install records the roster on
  the durable (Global) install-record value (`driver.py::_roster_value` →
  `l3_local_capacities`). No Local write at install (install has no per-user
  principal — that is a separate user-scoped-install concern).
* **Boot (register metadata, run no skill code).** A durable-path boot step
  (`boot.py`, after `boot_local`) registers each installed skill's capabilities
  **metadata-only** into the booting user's Local via
  `CapacityLayer.register_lazy_capacity` — a function-less `Capacity` built from
  the descriptor's declarative metadata; the skill's builder is **not** called,
  so boot runs no skill code and boot cost is flat regardless of install count.
  Descriptors are gathered from the durable install records and the user's Local
  `installed-capacities` role (the latter empty until user-scoped install ships).
  Best-effort (§am-2): a builder-unregistered or failing cap is logged +
  recorded on `Stack.local_caps_failed`, never bricks boot.
* **First use (build the function).** `_resolve_declaration` → `_maybe_build_lazy`
  (the single resolver shared by `cl.invoke` and the L4 dispatcher) sees a
  function-less capability with a stashed descriptor and builds the live function
  via its `reactivation_key` factory (`reactivation.build_declaration`), rebinds
  it, and returns it. Subsequent resolves reuse the bound function. A build
  failure raises `ReactivationError` (a `CapacityRegistrationError`) — the cap is
  unavailable for that call, no crash. Reachable unchanged through the `invoke`
  brain verb (dispatch resolves Local caps).

**No reconcile needed.** The CL Local capacity metagraph is rebuilt every boot,
so an uninstalled or upgraded skill needs no cleanup — boot registers exactly the
currently-`installed` records' caps. Uninstall/upgrade are handled by record
status/content read fresh each boot.

**Idempotency.** Metadata re-registers each boot with `if_exists="upsert"`; a
cap's new Local DataStates register with `register_datastate(if_exists="ignore")`
(added this amendment) since the Local DataState graph is minted fresh each boot.

**Scope / status.** Additive. Global admin install/activate unchanged; the
ephemeral path registers nothing. `installed-skills` install-record scope
(§am-6, Global-only) unchanged — only the *capability* is Local. Verified: L3
unit lifecycle (`tests/feat_skill_local_caps`) + durable install→boot→invoke +
verb reachability (`tests/resident_brain/test_skill_local_cap_durable.py`).

**Alternatives rejected.** (a) **Eager** (call the builder at boot) — reuses the
shipped reactivate rail but pays construction for every installed cap each boot;
rejected for the OS "start on use" property. (b) **`bind_impl` flag** (builder
returns metadata-only when asked) — pushes "skip heavy work" onto the author and
duplicates construction; rejected. The data/behavior split makes flat boot
structural (boot calls no skill code) with no author burden.

**Known debt.** The builder must be registered in-process at boot — relies on the
skill's installer module (imported by `apply_installed_skills`) registering its
`reactivation_key` factory at import. A missing registration surfaces as a
`local_caps_failed` entry at boot (before first use), not a mid-task surprise.
