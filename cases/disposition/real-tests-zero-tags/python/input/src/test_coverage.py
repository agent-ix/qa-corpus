# Two real pytest tests and not one trace tag anywhere in the tree. The shape is
# taken from data-store/tests/test_hashing.py, whose module docstring names the
# requirements in PROSE — `Covers: FR-001 (content addressing)` — and binds
# nothing, because `python-docstring-id` anchors on the FIRST token of the doc
# comment. That repository is one of 150 with test files and no binding tag at
# all.
#
# NOT MIXED, deliberately. Every other attachment and join fixture in this corpus
# pairs a defective tag with a correct one, because a degenerate all-defective
# tree fires `no-symbol-bound` for a reason that holds in no real repository.
# Here the degenerate tree IS the population: the authoring is absent, that is
# the whole disposition, and `no-symbol-bound` firing is the correct answer
# rather than an artefact of the fixture.
#
# No id is written anywhere in this file on purpose.


def test_defaults_every_finding_to_warning():
    severity = "warning"
    assert severity == "warning"


def test_names_the_declaration_on_every_finding():
    declaration = "traceability.trace_tags"
    assert declaration
