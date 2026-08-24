# THE SAME FILE WITH ONE TOKEN CHANGED: the id declared by the `## Invariants`
# table becomes the id declared by `## Acceptance Criteria`. Nothing else
# differs — same two tests, same docstring form, same position in the body, same
# sibling tag, same spec tree, same census.
#
# That is the whole repair, and it is why the pair is worth having. The failure
# case is not a missing tag, a misplaced tag or an unreadable tag: both ids are
# authored table rows with an `ID` column, in the same document, read by the
# same form. One id class is minted and the other is not.


def test_carries_the_declared_severity():
    """FR-001-AC-1: the declared severity is the one carried."""
    severity = "warning"
    assert severity == "warning"


def test_names_the_declaration_on_every_finding():
    """TC-002: the row's own minted id, which the declaration can join."""
    declaration = "traceability.trace_tags"
    assert declaration
