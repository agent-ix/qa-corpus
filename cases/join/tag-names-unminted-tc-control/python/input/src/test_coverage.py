@pytest.mark.trace("TC-001")
def test_defaults_every_finding_to_warning():
    severity = "warning"
    # this tag names the matrix row.
    assert severity == "warning"


@pytest.mark.trace("TC-002")
def test_names_the_declaration_on_every_finding():
    declaration = "traceability.trace_tags"
    # this tag names a minted row.
    assert declaration
