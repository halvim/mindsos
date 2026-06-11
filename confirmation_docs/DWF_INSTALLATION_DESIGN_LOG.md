# DWF_INSTALLATION — Design Log

Chat opened 2026-06-10, parallel to WSD_INSTALLATION_CHAT. Seed:
`projects/dwf_mapping/FUTURE_CHAT_PROMPT.md` (2026-05-28) with kickoff
overrides. Coordination contract: `WSD_INSTALLATION_DESIGN_LOG.md §3`.

## §0 — R0 probe findings (2026-06-10, all grep/file-verified)

- **P-1 (prereq).** `phase-50-confirmed` present; main at `7ef54f2`
  (after `cb5d207`). Untracked robot-demo/WSD-log corpus present —
  selective staging only.
- **P-2 (seed PB-7 dead).** `alignment_role()` returns
  `alignment:<a>:<b>` (sorted, `:` separator) per ADR-0154 / Phase 39
  L2-35; `validate_alignment_role_naming` uses the same helper.
  Reconciled — do not re-litigate.
- **P-3 (master TSV).** `oewn-dulplus-master.tsv`: 104,729 lines =
  **104,728 rows + header**, 16MB, **CRLF line endings**, 7 columns:
  `oewn_id, pos, dulplus_class, method, primary_lemma, provenance,
  gloss`. **No confidence column** — confidence derives from method
  priority (D-MI-3, B3).
- **P-4 (FrameNet corpus ABSENT).** `oewn-framenet-alignment.tsv`
  (38,998 mappings, v6) is **not in the repo** — ANALYSIS.md B2 already
  flags "NOT IN THE ZIP"; no `release-v6/` extraction present. Half the
  POST_PHASE_38 §6 DWF row is unbuildable as seeded.
- **P-5 (class-set probe — seed PB-3 mandate).** Corpus uses **64
  distinct classes**, not 207: 51 `dul:`, 4 `coll:`, 1 `conc:`,
  1 `ontopic:`, 1 `rol:`, 1 `owl:Thing`, 5 full-IRI forms
  (Conceptualization.owl / Supplements.owl). Non-`dul:` classes cover
  5,959 rows (5.7%). Hygiene defects: duplicate spellings of the same
  class (`conc:InternalRepresentation` vs full
  `...Conceptualization.owl#InternalRepresentation`), `owl:Thing` as a
  vacuous mapping target.
- **P-6 (paper pins).** `data/datasets/` does **not exist** —
  `dolce-dul-4.1.owl` and `oewn-2024.xml` referenced by
  `mindsos_admin/bootstrap.py` are not in the repo; the three shipped
  importers (`mindsos_admin/importers/{dolce,oewn,framenet}.py`) have
  only ever run against synthetic test fixtures. Meanwhile
  `english-wordnet-2025.ttl` (OEWN 2025) IS in
  `projects/dwf_mapping/source/`. `OewnImporter` parses WN-LMF XML
  only.
- **P-7 (anchors decouple).** `AlignmentAnchor` nodes carry
  `ref:<role>` properties — external IRIs referenced **by value**; the
  alignment pair-graph is self-contained. Alignment import does NOT
  require populated ontology/lexicon graphs. `build_alignment_schema`
  is ADMIN_AUTHORED, `strict` opt-in, `extra_edge_types` hook exists.
- **P-8 (ADR-0150 tier, re-grounded).** §am-1 (alignment Global-only at
  v1) **stands** — §am-5 (Phase 43) and §am-6 (Phase 50) touched other
  roles, not alignment tier. am-1 carries an explicit future-expansion
  clause for Local alignment.
- **P-9 (driver as-built, ADR-0183 / Phase 50).** `bundle_digest` =
  SHA-256 over **manifest bytes only** ("the reference bundle has no
  sidecar data files; a sidecar-file digest roster is a future
  amendment" — manifest.py header). L2 slot = inline declarative
  `L2ContentEntry` rows (unsuitable for 104k nodes). Only execution
  hook = `[l3].installers` `module:function` entry points resolved via
  importlib over **release-shipped** code. No knowledge-importer slot
  exists. The seed's "manifest + TSV data + importer-invocation L2
  slot" does not fit as-built.
- **P-10 (v2-trigger ledger).** Sidecar digests are NOT a ledger item
  (amendable without pull-forward). **Bundle upgrade path vN→vN+1 IS**
  a ledger item (owner WSD/maintenance) — the main lifecycle value of
  driver reuse cannot be pulled forward.
- **P-11 (disputed subset is actionable).**
  `doubtful-mappings-register.tsv` = 10,650 rows ≈ the 10.8%
  not-acceptable mass — seed PB-2 option (d) needs no new audit work.
- **P-12 (row-count discrepancy).** 107,518 (HANDOFF_latest §12 v4
  coverage sum) vs 104,728 (TSV) = 2,790 unexplained (multi-class
  collapse of 791 does not account for it alone).
- **P-13 (ADR-0182 fit).** Alignment edge metadata (confidence float,
  method str, provenance str, quality-tier str) are all primitives —
  no structured-value codec involvement; low risk.
- **P-14 (WSD §3 contract consumed).** Binding: alignment-density
  measurement (verb senses with (i) FrameNet alignment + (ii) DOLCE
  class) reported at import time; empirical-layer is WSD-owned; slot
  pool next-free 51, reserve at phase-map time in HANDOFF; single-tester
  gate serialization.

### R0.1 addendum — user-supplied corpora (2026-06-10 evening)

Henrique added `Dolce/`, `Framenet/`, `Maps/`, `Oewn/` under
`projects/dwf_mapping/`. Probe results:

- **P-15 (FrameNet alignment STILL absent).** `Framenet/` =
  **FrameNet v1.7 source corpus** (846MB, 14,931 XML files — frame/,
  lu/, fulltext/). This is the input the shipped `FramenetImporter`
  ingests (pin matches: "FrameNet 1.7"), NOT the missing
  `oewn-framenet-alignment.tsv` (38,998 rows). `Maps/` holds only the
  OEWN↔DOLCE master/alignment TSVs + TTL. **D-2 remains open.**
- **P-16 (wrong DOLCE family).** `Dolce/DLP3971/` = DOLCE-Lite-Plus
  397 (`loa-cnr.it/ontologies/...` namespaces). The corpus targets
  DOLCE+DnS Ultralite: `dul:` =
  `ontologydesignpatterns.org/ont/dul/DUL.owl#` (per the alignment TTL
  prefixes) + CollectionsLite/Roles/ontopic supplement modules.
  **Zero namespace overlap** with DLP3971. Note: the shipped
  DolceImporter pin "DOLCE-DUL 4.1" IS DUL.owl — so with the correct
  (freely downloadable, small) DUL.owl + 4 supplement modules, the
  shipped importer covers the corpus's 51 `dul:` classes (94.3% of
  rows) natively; the seed's 107-vs-207 drift framing dissolves.
- **P-17 (OEWN 2025 full).** `Oewn/english-wordnet-2025.ttl` = 198MB /
  5.4M lines (the `source/` copy was a 21-line stub). `OewnImporter`
  is WN-LMF **XML-only**; OEWN 2025 is also published as WN-LMF XML —
  obtaining the XML edition beats teaching the importer TTL.
- **P-18 (license/repo hygiene).** FrameNet 1.7 is click-through,
  "**NOT repo-shippable**" per the shipped importer docstring. 846MB
  now sits untracked inside the working tree; OEWN TTL adds 198MB.
  Must never be committed; `git add -A` ban now load-bearing.
- **P-19 (dedup).** `Maps/oewn-dulplus-master.tsv` is md5-identical to
  `source/` copy; pick one canonical location at phase-map time.

- **P-20 (intersection probe result, D-5/D-8 evidence).** Henrique
  fetched DUL.owl 4.1 + CollectionsLite/Roles/ontopic/Supplements/
  Conceptualization (note: server returns **Turtle under the `.owl`
  extension** — DolceImporter picks parser by extension → rename to
  `.ttl` or sniff at the endpoint slot). rdflib probe over all modules
  vs the master TSV: **97.92% of rows (102,548/104,728) resolve**;
  13 rows `owl:Thing`; **2,167 rows (2.07%) unresolved across 6
  classes**: `dul:State` 1,974 / `dul:System` 160 /
  `dul:CognitiveState` 16 / `dul:CognitiveEvent` 8 / `dul:Obligation`
  6 / `dul:Achievement` 3.
- **P-21 (the 6 are DWF inventions).** `dulplus.rdf` (wn30 extension,
  71KB) declares NO new classes — only axioms over the published
  modules; zero occurrences of the six names. They exist only in
  DWF's own `dulplus-reference.md`. The seed's 107-vs-207 drift
  framing is fully dissolved: real drift surface = 6 invented classes
  on 2.07% of rows. Non-blocking for slot 1 (P-7 by-value anchors).

## §1 — R0 pushbacks (status: PROPOSED 2026-06-10, awaiting Henrique)

### D-1 (headline) — driver reuse vs bare importer
Per P-9/P-10 the seeded reuse shape does not fit as-built and its main
payoff (upgrades) is ledger-locked to v2. Options: (a) full reuse now
via ADR-0183 amendment (knowledge-importer slot + sidecar digest
roster); (b) bare 4th release importer (Phase 15a regime); (c) bridge —
AlignmentsImporter ships as release code with an entry-point-compatible
signature, slot 1 runs it admin-side, bundle-wrap deferred to the v2
amendments where the ledger already routes upgrades.
**Pick: (c).** S10 justification: not a second provenance regime — it
is the existing importer regime (the same one DOLCE/OEWN/FrameNet
already use) kept forward-compatible with the driver; wrap lands with
the v2 sidecar/upgrade amendments.

### D-2 — FrameNet half of the §6 row is unbuildable (P-4)
Options: (a) Henrique supplies the release-v6 bundle before phase-map
authoring; (b) descope FrameNet to a gated slot 2 (gate = file present
+ row-count/digest assert), ship OEWN↔DOLCE in slot 1, density part (i)
reported PROVISIONAL from CHANGES_v5_to_v6 audit numbers; (c)
regenerate v6 in-chat — rejected (pipeline inputs/scripts incomplete in
repo; out of scope).
**Pick: (a) if the zip exists, else (b).** Slot structure isolates
FrameNet either way.

### D-3 — density measurement definition (WSD-binding, P-14)
Corpus is synset-level; (ii) is ~100% by construction — the informative
number is (i), which is FrameNet-gated (D-2). Options: (a) synset-level
denominator (verb synsets), measured against the imported graph,
test-asserted at import; (b) sense-level via lexicon sense nodes.
**Pick: (a)** + record the synset→sense note in WSD log §3. Needs WSD
confirmation (their gate).

### D-4 — precision tier (seed PB-2 + PB-5 together, re-grounded P-8/P-11)
Options: (a) Global as-is, confidence only; (b) Local + promote —
rejected (am-1 amendment with no Local consumer; conflicts release
model); (c) pause for v7 — rejected (indefinite); (d) Global +
per-edge disputed/quality-tier flag sourced from the doubtful register
+ confidence from method priority.
**Pick: (d).** No ADR amendment; consumers filter/weight; register
rows ≈ exactly the 10.8%.

### D-5 — version drift (seed PB-3, reframed by P-5/P-6/P-7)
There is no loaded DOLCE/OEWN data to drift against — pins are paper.
P-7 decouples alignment import from lexicon/ontology population.
Options: (a) hold pins + re-run DWF pipeline — rejected (months);
(b) bump pins toward DWF (OEWN 2025 TTL in repo; but OewnImporter is
XML-only — scope widens); (c) intersection-only import — rejected
(nothing loaded to intersect against at runtime).
**Pick: defer the pin bump out of DWF slot 1** (anchors make it
non-blocking); ship a **class-normalization table** (dual-spelling
merge, `owl:Thing` policy, Supplements/extension-module classes
documented) + a version-audit section in the import report. Pin bump
routed to a later slot or MAINTENANCE.

### D-6 — row-count discrepancy (P-12)
**Pick:** TSV is canonical; tests assert exactly 104,728; the 2,790
delta recorded as an audit item, non-blocking.

### D-7 — importer body sub-decisions (seed PB-1a-d, mostly forced)
Input = master TSV (only format present; DWF-PB-1 bundles absent);
multi-class: master is post-collapse — secondary edges from the
register NOT imported at v1 (revisit with D-4 data in place);
idempotency: MERGE-semantics on (anchor IRI, edge identity) per Phase
15a contract; validation: hybrid per ADR-0139; CRLF + normalization
(D-5) handled importer-side with counts in stats.
**Pick: as stated.** Body design detail belongs to R1.

### D-8 (new, R0.1) — wrong DOLCE ontology supplied (P-16)
Options: (a) obtain DUL.owl 4.1 + the 4 supplement modules
(CollectionsLite, Roles, ontopic, Supplements/Conceptualization) —
small, freely downloadable; (b) endpoint-free import only (P-7 anchors)
— ontology never loaded in DWF; (c) mint a 64-class ad-hoc ontology
from `dulplus-reference.md` — rejected (improvises an ontology when the
real one is downloadable).
**Pick: (b) for slot 1 (unchanged); (a) for the endpoint slot (D-10).**
DLP3971 set aside — not consumed by anything.

### D-9 (new, R0.1) — license/repo hygiene (P-18)
Options: (a) `.gitignore` `projects/dwf_mapping/{Framenet,Oewn,Dolce,Maps}/`
immediately + record the canonical external-data convention
(`data/datasets/` stays the bootstrap path, gitignored); (b) move data
out of the repo tree. **Pick: (a) now** (one-line change, removes the
accident surface), (b) optional later.

### D-10 (new, R0.1) — endpoint loading: in DWF scope?
The delivery implies endpoints should become real (first production
data ever loaded). Options: (a) dedicated endpoint slot AFTER the
alignment slot — run shipped FramenetImporter (1.7 XML ready),
DolceImporter (needs DUL.owl per D-8a), OewnImporter (needs OEWN 2025
WN-LMF XML; bump the 2024 paper pin to 2025 — costs nothing, nothing
loaded anywhere, and aligns the pin with the corpus the alignment was
built from); (b) out of DWF scope (alignment-only boundary per WSD §3)
— route to ops/bootstrap; (c) fold into slot 1 — rejected (slot 1 is
endpoint-independent per P-7; keep it small).
**Pick: (a).** Zero new design — shipped importers + pin-doc
amendment; and it converts the seed's PB-3 from "drift audit" into
"pins follow the corpus".

### D-11 (new, R0.1) — the 6 DWF-invented classes (P-20/P-21)
Options: (a) declare them as a 6-node admin-authored extension at
endpoint load (subclass placement per `dulplus-reference.md`: State ⊑
Event, CognitiveEvent ⊑ Event, CognitiveState ⊑ State, Achievement ⊑
Event, System / Obligation placed per reference), provenance-tagged
`dwf-extension`, keeping corpus IRIs as-is; (b) remap the 2,167 rows
to nearest declared ancestor — loses granularity (1,974 State rows
collapse into Event); (c) drop the rows.
**Pick: (a).** Corpus fidelity preserved; 13 `owl:Thing` rows dropped
with the count asserted in stats.

## §2 — Coordination note owed to WSD log §3
After R0 acceptance: density definition (D-3 pick), FrameNet gating
state (D-2), slot reservation when made.
