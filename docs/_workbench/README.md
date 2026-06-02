# `docs/_workbench/`

Transient working documents — handoffs, plans, design baselines, chat seeds — that are useful while a workstream is active, then deprecate.

**Lifecycle.** A doc lands here when a chat opens it (e.g., a chat baseline, a plan-of-record, a re-litigation seed). It stays here while the workstream is live. When the workstream lands (ship, archive, or supersede), the doc either (a) migrates to a permanent home (`docs/dev/`, `confirmation_docs/`, `docs/decisions/adr/`, etc.) if it has lasting value, or (b) gets deleted, or (c) gets moved into `_archive_Layered_Intelligence/` if forensic-only.

**What lives here.**
- Live indexes of in-flight work routed across phases + downstream chats (`L0_FUTURE_WORK.md` ... `L5_FUTURE_WORK.md`). Each carries a Chat-C-closure routing table; items deplete as phases land or downstream chats consume them.
- Live ship-tracking surfaces (e.g., `STREAM_A_BACKLOG.md` for the Chat C Stream A bug-fix PR queue).
- Live routing tables (e.g., `cookbook_routing.md`).
- Re-litigation seeds drafted mid-chat.
- Cross-chat coordination notes during multi-chat workstreams.

Closed-class decision logs migrate to `confirmation_docs/` when their authoring chat closes (Chat A/B/L1-L3 reframe/L2 chat/Chat C closure logs migrated 2026-06-02; see HANDOFF §10 for the full migration map).

**What does NOT live here.**
- Shipped ADRs → `docs/decisions/adr/`.
- Permanent design notes → `docs/dev/`.
- Phase artifacts → `confirmation_docs/`.
- End-user docs → `docs/usage/`, `docs/concepts/`, etc.

**Convention.** Leading underscore matches `_archive_Layered_Intelligence/` — both signal ephemeral state. `_workbench/` is the live equivalent of `_archive_`.
