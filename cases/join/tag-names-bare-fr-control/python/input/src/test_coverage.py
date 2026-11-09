# The SAME file with FOUR CHARACTERS added to one tag: the bare requirement id
# becomes the criterion id the declaration mints. Nothing else differs — same
# two tests, same comment form, same position in the body, same sibling tag.
#
# That is the whole repair, and it is why the pair is worth having: the failure
# case is not a missing tag, a misplaced tag or an unreadable tag. It is a tag
# the engine reads perfectly and joins to nothing.


@pytest.mark.trace("TC-001", "FR-001-AC-1")
def test_defaults_every_finding_to_warning():
    severity = "warning"
    # every finding defaults to warning.
    assert severity == "warning"


@pytest.mark.trace("TC-002")
def test_names_the_declaration_on_every_finding():
    declaration = "traceability.trace_tags"
    # the row's own minted id, which the declaration can join.
    assert declaration
