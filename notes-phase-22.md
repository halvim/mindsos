# Phase 22 — Server: admin ops (tester notes)

Six admin user-management verbs landed under `mindsos server admin`
Typer subgroup: `promote-user`, `demote-user`, `disable-user`,
`enable-user`, `kill-session`, `hard-delete-user`. Plus the
long-deferred `_assert_not_sole_admin` helper + `LastAdminError` class
from Phase 20 PB-B closure. Plus `admin_tx` `BEGIN IMMEDIATE` wrapper
closing the SQLite WAL concurrent-admin race (R4 PB-24 load-bearing
catch).

Cross-user read (ADR-0008 `read_other_local`) DEFERRED to Phase 25
alongside `MindsOSServer` + `LocalPersister` per R1 PB-1 + ADR-0008
§amendment-1 — Phase 22 has no working substrate for the §Decision
refcount-install model.

## Design

27 picks across 5 design rounds. See
`confirmation_docs/PHASE_22_DESIGN_LOG.md` for the full ledger.

ADR amendments at this ship:

* **ADR-0012 §amendment-3** — 6-clause batch: closes PB-B deferral
  from §am2; ships `_assert_not_sole_admin` + `LastAdminError` + 6
  verb roster; documents `admin_tx` BEGIN IMMEDIATE race protection;
  records `NotAnAdminError` message rework (verb-agnostic) per R4
  PB-25; locks the extended exit-code namespace (3/4/5/6).
* **ADR-0008 §amendment-1** — phase-placement amendment; first
  consumer of cross-user read shifts P22 → P25.

ADR-0002 NOT amended (`CAN_HARD_DELETE_ARCHIVED` cap-name mismatch
per R2 PB-17 is documentary debt; rename is breaking per
§Consequences — defer to dedicated rename ADR).

## Manual smoke (host-native via `mindsos` binary)

Per `feedback_smoke_harness_host_native.md` — host-native is the
canonical smoke harness; `docker compose run --rm` has no
`~/.mindsos/` mount.

### Setup

```bash
# Clean slate
rm -f ~/.mindsos/server.db ~/.mindsos/token

# Bootstrap admin
echo "adminpw" | mindsos server bootstrap admin

# Login
echo "adminpw" | mindsos server login admin

# Create a second user
echo "alicepw" | mindsos server user create alice
```

### Promote / demote round-trip

```bash
# alice (user) → admin
mindsos server admin promote-user alice
# Expect: verb=admin_promote_user target='alice' prior_role='user' (exit 0)

# Re-promote already-admin → AlreadyAnAdminError (exit 5)
mindsos server admin promote-user alice
# Expect: exit code 5

# Demote alice back to user (alice has no sessions; sessions_killed=0)
mindsos server admin demote-user alice
# Expect: verb=admin_demote_user target='alice' prior_role='admin' sessions_killed=0

# Demote sole admin 'admin' → LastAdminError (exit 4)
mindsos server admin demote-user admin
# Expect: exit code 4; message names 'reset-admin' as override
```

### Disable / enable round-trip

```bash
mindsos server admin disable-user alice
# Expect: verb=admin_disable_user target='alice' sessions_killed=0

# Idempotent disable
mindsos server admin disable-user alice
# Expect: exit 0, output marker [already_disabled]

mindsos server admin enable-user alice
# Expect: verb=admin_enable_user target='alice'

# Idempotent enable
mindsos server admin enable-user alice
# Expect: exit 0, output marker [already_enabled]
```

### Kill session

```bash
# Login as alice in another shell to create a session
echo "alicepw" | mindsos server login alice

# As admin: query audit to find alice's session_id
mindsos server query-audit --actor alice --event EVT_LOGIN --json | jq .rows

# Kill a specific session by ID
mindsos server admin kill-session <session_id>
# Expect: verb=admin_kill_session target_session_id=... target_user_id='alice'

# Missing session_id → SessionNotFoundError (exit 6)
mindsos server admin kill-session nope
# Expect: exit code 6
```

### Hard delete

```bash
# Create a throwaway user
echo "bobpw" | mindsos server user create bob

# Hard-delete bob
mindsos server admin hard-delete-user bob --json
# Expect: payload includes prior_role='user', was_disabled=false, sessions_killed=0

# Hard-delete sole admin → LastAdminError (exit 4)
mindsos server admin hard-delete-user admin
# Expect: exit code 4

# Verify audit row outlives the user row
mindsos server query-audit --target bob --event EVT_HARD_DELETE_USER --json | jq .rows
# Expect: one row with target='bob' (no FK to users; survived the DELETE)
```

### Capability denial

```bash
# Promote alice back to user, then login as alice (no admin caps)
mindsos server admin promote-user alice  # if you demoted earlier, ignore the AlreadyAnAdminError
# (skip: re-bootstrap a non-admin caller via user create + login)

# Try an admin verb from a non-admin session → exit 3 + EVT_PERMISSION_DENIED
echo "alicepw" | mindsos server login alice
mindsos server admin promote-user bob
# Expect: exit code 3
```

## Pass criteria

- `pytest tests/phase_22/` green isolated (~16 files; 0 failed, 0 skipped)
- `pytest tests/` green cumulative
- `pytest tests_server/integration/test_layer_isolation.py` green (no `from mindsos_server` in domain pkgs)
- `mindsos doctor --self-test` green on phase-22 branch (6-pkg parity at `0.0.0+phase22`; schema_version still 3)
- `confirmation_docs/PHASE_22_DESIGN_LOG.md` committed
- ADR-0012 §amendment-3 + ADR-0008 §amendment-1 committed at the parent /Layered Intelligence/docs/decisions/adr/ tree
- `phase-22-confirmed` tag pushed AFTER squash-merge of PR; `release.yml` green

## Known foot-guns (documented for operators)

- **Self-demote / self-disable / self-hard-delete** all allowed per
  PB-18; `_assert_not_sole_admin` enforces "another admin exists"
  before destructive self-targeting. If the caller is the only admin,
  the helper fires LastAdminError (exit 4). If the caller has a peer
  admin, they can lock themselves out — recovery via filesystem
  `mindsos server reset-admin <peer_admin_id>` or via `bootstrap`
  on a fresh DB.
- **Capability-string cap name `CAN_HARD_DELETE_ARCHIVED`** is
  misleading — no "archive" step exists; the cap name implies
  destructive-ops-on-archived-users but Phase 22 hard-deletes any
  user regardless of disabled state. Documentary debt; rename
  deferred per ADR-0002 §Consequences.
- **`hard_delete_user` does NOT cascade to KL Local** — only the
  user row + session rows are deleted. Local cleanup is a KL phase
  concern (deferred to a future KL phase). Operators running KL with
  hard-deleted users will see orphaned Local instances until that
  phase ships.
- **Concurrent admin verbs serialize through `admin_tx` BEGIN
  IMMEDIATE** — second verb may wait up to `busy_timeout=5000` ms;
  beyond that, SQLITE_BUSY raises. Acceptable for CLI single-shell
  deployment. Reset-admin does NOT yet use `admin_tx` (known
  minor inconsistency; flagged for future cleanup).

## Phase 23 handoff

Exit artifact: `confirmation_docs/PHASE_23_NEXT_CHAT_PROMPT.md`.
Phase 23 = Server: MetagraphSnapshot rollback infrastructure
(narrowed). May itself retire to Phase 24 if its design chat decides
the snapshot wrapper has no real consumer until Phase 24's
`release_update` lands.
