"""A Local-tier skill bundle (CORE-C2R1 — ADR-0150 §amendment-11).

The Phase-50 reference bundle (``skill_bundle_ref``) declares every
``[[l2.content]]`` entry at ``tier = "global"``, so installing it needs
``CAN_WRITE_GLOBAL`` no matter who runs it. That made it useless for
exercising the thing §am-11 exists for: **a user installing a Skill into
their own realm.**

This bundle declares its content at ``tier = "local"``, in
``request-patterns`` — dual-scope since ADR-0150 §am-8. It carries no
``[l3]`` section: C2R1's subject is *where the install record and the
bundle's content land, and who can see them*, not capacity registration,
which the reference bundle already covers.

**What its existence proves, and the limit it marks.** A bundle can only
be user-installable if its content is Local-tier. Nothing in the shipped
bundle format stops an author writing ``tier = "global"``, and most
useful content — concepts, ontology — lives in Global-only roles a user
cannot write. So §am-11 delivers the substrate; **which bundles are
genuinely user-installable is a skill-packaging question**, and is the
unbuilt Local half of ADR-0183 §am-5.
"""

from pathlib import Path

#: The bundle's manifest path, for tests.
MANIFEST_PATH = Path(__file__).parent / "manifest.toml"
