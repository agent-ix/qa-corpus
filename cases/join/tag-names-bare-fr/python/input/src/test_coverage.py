# The shape is taken from agent-duncan/tests/unit/test_executor.py:2234 — a
# `#` comment carrying a BARE requirement id, inside the test body, on the
# assertion it justifies.
#
# The tag BINDS. `python-comment-id` admits `FR-\d+` and the enclosing symbol is
# a test function, so this is a healthy binding by every measure the engine has:
# the census counts it, and it counts it as bound. What it binds to is an id the
# declaration never minted.
#
# MIXED on purpose — one bare requirement id beside one minted test-case id.


def test_defaults_every_finding_to_warning():
    severity = "warning"
    # FR-001: every finding defaults to warning.
    assert severity == "warning"


def test_names_the_declaration_on_every_finding():
    declaration = "traceability.trace_tags"
    # TC-002: the row's own minted id, which the declaration can join.
    assert declaration
