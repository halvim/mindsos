"""``install_prompt_edition_capacities`` — plan item I-16.

I-9 shipped the writer with no installer, so the capacity was a declaration no
registry held and L4 could not route to it. These are the claims the installer
makes; that the CLASS of defect cannot recur is
``tests/architecture/test_registry_capacity_has_an_installer.py``.
"""

from __future__ import annotations

import pytest

from mindsos_capacity import CapacityLayer, CapacityRegistrationError
from mindsos_capacity.bootstrap import ensure_datastate_graph
from mindsos_capacity.builtins.prompt_edition_v0 import (
    DS_PROMPT_EDITION_WRITE,
    install_prompt_edition_capacities,
    prompt_edition_datastates,
)
from mindsos_capacity.identifiers import CATEGORY_COMPREHENSION, capacity_iri


CAP_IRI = capacity_iri(CATEGORY_COMPREHENSION, "write_prompt_edition")


def test_install_registers_the_capacity_and_its_datastate():
    layer = CapacityLayer()
    install_prompt_edition_capacities(layer)

    assert CAP_IRI in {d.iri for d in layer.iter_declarations()}
    graph = ensure_datastate_graph(layer.global_metagraph(), strict=layer._strict)
    assert DS_PROMPT_EDITION_WRITE in graph.nodes


def test_the_installed_declaration_still_declares_its_write():
    """The installer must not register some other shape than the one I-15
    gave the factory: registered and unable to write is the same dead end in
    a different costume."""
    layer = CapacityLayer()
    install_prompt_edition_capacities(layer)
    declaration = next(
        d for d in layer.iter_declarations() if d.iri == CAP_IRI
    )
    assert declaration.writes is True
    assert declaration.outputs == ()


def test_install_is_idempotent():
    layer = CapacityLayer()
    install_prompt_edition_capacities(layer)
    install_prompt_edition_capacities(layer)
    assert len([d for d in layer.iter_declarations() if d.iri == CAP_IRI]) == 1


def test_partial_install_state_is_refused():
    """The DataState present and the capacity absent is a half-installed
    family, and the installer says so instead of completing it silently -
    the ``install_text_capacities`` precedent."""
    layer = CapacityLayer()
    for datastate in prompt_edition_datastates():
        layer.register_datastate(datastate)

    with pytest.raises(CapacityRegistrationError, match="partial install state"):
        install_prompt_edition_capacities(layer)
