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

**It is the first bundle a non-admin can install.** Phase-50 preflight
refused every non-Global tier outright (S3, *"Local = v2 trigger"*), so
§am-11's Local install record had no bundle it could carry. ADR-0183
§amendment-6 amends S3: the **tier** says which realm the content wants,
the **role** says which realms can hold it. ``request-patterns`` is
dual-scope, so this bundle passes; ``tier = "local"`` on ``concepts``
still does not.

**The limit it marks.** Most useful content — concepts, ontology — lives
in Global-only roles, so a user-installable bundle is a narrow thing
today. Which bundles *should* be user-installable, and what a Skill may
legitimately place in a user's realm, is a **skill-packaging** question
and is the unbuilt Local half of ADR-0183 §am-5.
"""

from pathlib import Path

#: The bundle's manifest path, for tests.
MANIFEST_PATH = Path(__file__).parent / "manifest.toml"
