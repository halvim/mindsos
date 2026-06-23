"""Task 1 gate — bongard.* realm + ontology atoms register Local.

Asserts the new-realm registration works with no core change (G0) and
every ontology atom lands in the session's Local DataState graph with a
well-formed ``bongard.<suffix>`` IRI.
"""

from __future__ import annotations

import pytest

from bongard import BONGARD_REALM, ONTOLOGY, build_instance
from bongard.ontology import register_ontology
from bongard.harness import DuckSession

from mindsos_capacity import CapacityLayer
from mindsos_capacity.exceptions import CapacityRegistrationError


def test_build_instance_registers_every_atom():
    cl, session = build_instance()
    view = cl.local_view(session.user_id)
    for ds in ONTOLOGY:
        assert view.get_datastate(ds.iri) is not None, (
            f"{ds.name} not registered Local"
        )


def test_atoms_are_single_dot_bongard_realm():
    for ds in ONTOLOGY:
        realm, _, suffix = ds.name.partition(".")
        assert realm == BONGARD_REALM
        assert suffix and "." not in suffix, f"{ds.name} not single-dot"


def test_new_realm_requires_allow_new_realm_flag():
    # Without allow_new_realm the bongard realm is rejected — proves G0's
    # claim that the flag (not a core change) is what licenses the realm.
    cl = CapacityLayer()
    session = DuckSession()
    with pytest.raises(CapacityRegistrationError):
        cl.register_datastate(ONTOLOGY[0], session=session, allow_new_realm=False)


def test_register_ontology_is_idempotent_only_via_fresh_layer():
    # Re-registering on the SAME layer raises by contract (no upsert for
    # DataStates); a fresh instance is the clean path.
    cl, session = build_instance()
    with pytest.raises(CapacityRegistrationError):
        register_ontology(cl, session)
