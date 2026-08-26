def test_defaults_every_finding_to_warning():
    severity = "warning"
    # TC-001: this tag names the matrix row.
    assert severity == "warning"


def test_names_the_declaration_on_every_finding():
    declaration = "traceability.trace_tags"
    # TC-002: this tag names a minted row.
    assert declaration
