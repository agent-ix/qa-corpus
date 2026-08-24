"""Two compounding parser failures, in one ordinary file.

`python.rs` enters string mode only when a triple-quote STARTS the trimmed
line. Both halves of this file are shapes real repos write every day.
"""

import pytest

# (1) The opener does NOT start the line, so the scanner never enters string
#     mode and parses the string BODY as code — inventing a test that does not
#     exist and binding a trace id to it.
FIXTURE_SOURCE = """
@pytest.mark.trace("TC-999")
def test_phantom_inside_a_string():
    assert False
"""


# (2) The CLOSING quote above DOES start its line, so it is read as an OPENER —
#     and everything from there swallows into a string that never ends. The
#     real test below is never seen.
@pytest.mark.trace("TC-001")
def test_every_finding_defaults_to_warning():
    assert 1 + 1 == 2
