# The SAME file with the banner citation moved off module scope and written as
# the marker on the test it names. Nothing else differs: same two tests, same
# two ids.
import pytest


# ---------------------------------------------------------------------------
# Warning default
# ---------------------------------------------------------------------------


@pytest.mark.trace("TC-001")
def test_defaults_every_finding_to_warning():
    assert 1 + 1 == 2


@pytest.mark.trace("TC-002")
def test_names_the_declaration_on_every_finding():
    assert 2 + 2 == 4
