# The SAME file with the banner tag moved off module scope and onto the test it
# names. Nothing else differs: same two tests, same two ids, same comment form.
import pytest


# ---------------------------------------------------------------------------
# Warning default
# ---------------------------------------------------------------------------


# TC-001: on the test, which registers an evidence symbol.
def test_defaults_every_finding_to_warning():
    assert 1 + 1 == 2


# TC-002: unchanged.
@pytest.mark.trace("TC-002")
def test_names_the_declaration_on_every_finding():
    assert 2 + 2 == 4
