# Coordinated Change Handoff — L0 Server: User Settings Table for ALS Training Preferences

**Date:** 2026-04-29
**Origin:** WSD subsystem design conversation (Word Sense Disambiguation project, Henrique Alvim).
**Purpose:** Surface a small L0 Server extension required by the ALS (Audited Learning Subsystem) — per-user training preferences as system configuration.
**Status:** Pre-implementation. Architectural specification only.
**Depends on:** Independent of L1/L2/L3/L4 changes. Can ship in parallel with any of them.

---

## 0. How to use this document

Upload to the L0 / Server design chat. Self-contained.

L0 owns: identity, sessions, capability enforcement, audit, user settings. This handoff specifies one new piece of state (user training preferences) to be managed alongside existing user identity / session machinery.

The change is small. This document is short.

---

## 1. Why this handoff exists

The ALS (Audited Learning Subsystem) lets users control which parameter families their Local system trains on, with what priority, under what audit policy override. These are **system configuration / settings** — operational metadata about how the system should behave for this user — not knowledge.

Per the WSD design conversation, settings are not L2 Knowledge content. The right home is L0 Server, alongside user identity, capabilities, and audit log. L0's `server.db` SQLite already manages `users`, `sessions`, `audit_log`. User settings extend the same pattern.

---

## 2. Summary

One change: **a new `user_settings` table in `server.db`** holding per-user, per-parameter-family training preferences.

Read by L4 via `Session` at the start of every dream training cycle. Written by L4 / admin tooling on user request.

---

## 3. The `user_settings` table

### 3.1 Schema

In `server.db` (SQLite), per the existing pattern of L0 tables:

```sql
CREATE TABLE user_settings (
    user_id          TEXT NOT NULL,
    setting_key      TEXT NOT NULL,
    setting_value    TEXT NOT NULL,        -- JSON-encoded value
    updated_at       TEXT NOT NULL,        -- ISO8601 timestamp
    updated_by       TEXT NOT NULL,        -- user_id of who updated (self or admin)
    PRIMARY KEY (user_id, setting_key),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX idx_user_settings_user ON user_settings(user_id);
```

The `setting_key` namespace is dotted; `setting_value` holds JSON-encoded values for flexibility.

### 3.2 Setting keys for ALS training preferences

Keys used by ALS:

  - **`als.training_enabled`** (bool) — master switch. Default: `true`.
  - **`als.parameter_set.<parameter_set_iri>.enabled`** (bool) — per parameter family. Default: `true`.
  - **`als.parameter_set.<parameter_set_iri>.priority`** (string: `low | normal | high`) — Default: `normal`.
  - **`als.parameter_set.<parameter_set_iri>.audit_policy_override`** (string: `auto-apply | batched-summary | individual-review` or null) — Default: null. Override is more-conservative-only; setting `auto-apply` when subsystem declared `individual-review` is rejected.
  - **`als.notes`** (string) — free-text user rationale.

Other setting keys could be added over time:

  - Privacy / consent settings (which data leaves Local).
  - Resource budgets (compute, dream cycle frequency).
  - Notification preferences.
  - Display preferences.

This handoff scopes to the ALS-related keys; other categories handled separately as needs surface.

### 3.3 Validation

L0 validates writes:

  - `user_id` exists in `users` table.
  - `setting_key` matches a known prefix (admin-extended whitelist; reject unknown keys to prevent typo-based silent failures).
  - `setting_value` is valid JSON.
  - For audit_policy_override: rejected if less conservative than the subsystem's declared policy (L0 needs to query L4 / L2 for the declared policy; or L4 validates this when reading and treats the override as "max conservativeness, ignore if less conservative").

Recommendation: L0 stores the value as-is; L4 enforces the more-conservative-only constraint at read time (L0 doesn't need to know L4's audit policies). Cleaner separation; L0 stays L4-agnostic.

### 3.4 Read access via Session

L4 reads settings through the `Session` object (per server handoff §2 — `Session` already carries user_id and capabilities).

Either:

  - **Eager load** — `Session` carries a `settings: dict[str, Any]` field populated at session creation.
  - **Lazy load** — `Session.get_setting(key) -> Any` queries `user_settings` table on demand.

Recommendation: lazy load. Settings change rarely; eager load wastes memory. `Session.get_settings(prefix="als.")` for batch retrieval.

### 3.5 Audit

Existing L0 audit log (per server handoff §10) gains a new event type:

  - **`USER_SETTING_CHANGED`** — fields: `user_id`, `setting_key`, `old_value`, `new_value`, `changed_by`.

This event fires on every write to `user_settings`. Provides admin visibility into preference changes.

---

## 4. Endpoints / API

L0 server gains:

  - **`get_user_setting(session, user_id, setting_key) -> SettingValue`** — read. Permission: user can read their own; admin can read anyone's (capability-gated).
  - **`set_user_setting(session, user_id, setting_key, setting_value) -> None`** — write. Permission: user can write their own (limited to known key prefixes); admin can write anyone's.
  - **`list_user_settings(session, user_id, prefix=None) -> list[Setting]`** — list with optional key-prefix filter.
  - **`reset_user_setting(session, user_id, setting_key) -> None`** — delete (revert to default).

Endpoints follow existing L0 patterns (per server handoff §4). Capability constants extend:

  - `CAN_READ_OWN_SETTINGS` — defaulted on for `user` role.
  - `CAN_WRITE_OWN_SETTINGS` — defaulted on for `user` role; can be admin-disabled per user (e.g., shared kiosks).
  - `CAN_READ_ANY_SETTINGS` — admin only.
  - `CAN_WRITE_ANY_SETTINGS` — admin only.

These are added to `mindsos_server.capabilities` per existing pattern.

---

## 5. Coordinated implications across other layers

### L1 — Core

  - No impact. Settings live in `server.db`, not in any metagraph.

### L2 — Knowledge

  - No impact. Settings are explicitly separate from L2 Knowledge per the WSD design conversation.

### L3 — Capacity

  - No direct impact. L3 capacities don't read settings.

### L4 — Intelligence

  - **L4 reads settings via Session** at start of every dream training cycle. ALS uses settings to gate per-user training behavior (which subsystems train, at what priority, with what audit policy override).
  - **L4 enforces more-conservative-only audit override** when reading the override setting (per §3.3).

### L5 — Mental Model

  - No impact.

### Future: Web UI / admin tooling

  - Settings are user-facing configuration; UX work to surface them (preference panels, admin user-management) defers to UI design sessions.

---

## 6. Open questions for L0 chat

  1. **Setting-key prefix whitelist** — should L0 maintain a list of known prefixes (`als.*`, `privacy.*`, `notifications.*`) and reject unknown ones at write time? Or accept any key and rely on L4 / consumers to ignore unknown keys? Recommendation: whitelist with admin-extension capability — typo prevention is worth the overhead.
  2. **Eager vs lazy session loading** (per §3.4). Recommendation: lazy.
  3. **Default values** — where do defaults live? Hardcoded in L4 (consumer-defined) or stored in L0 with admin-tunable defaults? Recommendation: L4-defined defaults (each ALS subsystem registration declares its default); L0 stores only user overrides.
  4. **Migration** — when a new ALS subsystem registers, all existing users implicitly opt in (via the L4-defined default). They can opt out by writing a `*.enabled = false` setting. Confirm acceptable, or do we want explicit opt-in?
  5. **Setting-value size limit** — JSON-encoded value should be bounded (e.g., 4KB max). Settings are configuration, not data dumps.
  6. **Cascade on user deletion** — `ON DELETE CASCADE` per the schema sketch. User deletion (per existing admin tools) clears their settings. Confirm.
  7. **Backup/restore** — settings are part of `server.db`; existing backup-via-`cp server.db` covers them per server handoff §3.1. Confirm sufficient.

---

## 7. Phasing

This handoff is small enough to ship in one PR:

  - Schema migration (add `user_settings` table + index).
  - New endpoints (`get/set/list/reset_user_setting`).
  - Capability constants + permission checks.
  - `Session` accessor methods (`Session.get_setting`, `Session.get_settings`).
  - Audit event type.
  - Tests for happy path + permission denied + invalid keys.

Estimated: ~150 LOC + tests. Single phase.

Can ship before, in parallel with, or after L1/L2/L3/L4 changes. L4's ALS implementation needs this to be ready when ALS lands; otherwise no dependency.

---

## 8. What this does NOT change

  - **Existing `users`, `sessions`, `audit_log` tables unchanged.**
  - **Existing endpoints and capability constants preserved.**
  - **Session contract (`Session` dataclass shape per server handoff §2) extended only with accessor methods, not new required fields.**
  - **Bootstrap / reset-admin / lifecycle behavior preserved.**
  - **No L2 / L3 / L4 layer changes triggered by this handoff specifically.** (Other coordinated-change handoffs trigger their own changes; this one is L0-only.)

---

## 9. Summary checklist for the L0 chat

When this handoff is implemented, L0 should have:

  - [ ] `user_settings` table in `server.db` (with schema migration).
  - [ ] Endpoints: `get_user_setting`, `set_user_setting`, `list_user_settings`, `reset_user_setting`.
  - [ ] Capability constants: `CAN_READ_OWN_SETTINGS`, `CAN_WRITE_OWN_SETTINGS`, `CAN_READ_ANY_SETTINGS`, `CAN_WRITE_ANY_SETTINGS`.
  - [ ] `Session.get_setting` / `Session.get_settings` accessor methods.
  - [ ] `USER_SETTING_CHANGED` audit event.
  - [ ] Setting-key prefix whitelist + validation.
  - [ ] Tests covering permission paths.

---

**End of handoff.**

When L0 design settles these changes, please update this document or write a follow-up handoff so the WSD design chat can absorb the final API.
