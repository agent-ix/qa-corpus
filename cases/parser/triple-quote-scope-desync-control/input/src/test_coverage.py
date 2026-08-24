"""The SAME file with the opening triple-quote moved onto its own line.

Byte-for-byte identical content otherwise — the same phantom text inside the
same string, the same real test after it. The only change is that the opener
now STARTS its line, which is the one condition `python.rs` checks.
"""

import pytest

# The opener starts the line, so the scanner enters string mode, skips the
# body, and the closing quote correctly ENDS the string rather than starting
# another one.
FIXTURE_SOURCE = (
"""
@pytest.mark.trace("TC-999")
def test_phantom_inside_a_string():
    assert False
"""
)


# So the real test below is seen, and it backs its row.
@pytest.mark.trace("TC-001")
def test_every_finding_defaults_to_warning():
    assert 1 + 1 == 2
