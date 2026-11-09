# The shape is taken from identity/tests/test_tenant_auth_policy.py:195 — a
# marker carrying a sub-id declared by an `## Invariants` table on an FR
# document.
#
# The tag BINDS. The marker admits the sub-id segment, the enclosing
# symbol is a test function, and the census counts it as bound. What it binds to
# is an id no target mints, because `## Invariants` is a heading NEITHER module
# declares: not in the ISO `FR` skeleton, not in either manifest. 15
# repositories author it anyway, 129 rows, and its table is the `Constraints`
# table under a different name.
#
# MIXED on purpose — one undeclared-section id beside one minted test-case id.

import pytest


@pytest.mark.trace("FR-001-INV-1")
def test_carries_the_declared_severity():
    """the declared severity is the one carried."""
    severity = "warning"
    assert severity == "warning"


@pytest.mark.trace("TC-002")
def test_names_the_declaration_on_every_finding():
    """the row's own minted id, which the declaration can join."""
    declaration = "traceability.trace_tags"
    assert declaration
