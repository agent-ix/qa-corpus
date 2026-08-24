# The SAME two tests with a tag added to each, in the form the declaration
# reads. Nothing else differs: same names, same bodies, same assertions.
#
# This is the disposition the failure case must be told apart from. Both trees
# have real tests; one has been authored against the matrix and one has not.


# TC-001: the row this test answers.
def test_defaults_every_finding_to_warning():
    severity = "warning"
    assert severity == "warning"


# TC-002: the row this test answers.
def test_names_the_declaration_on_every_finding():
    declaration = "traceability.trace_tags"
    assert declaration
