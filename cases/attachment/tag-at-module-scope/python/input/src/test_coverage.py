# A citation written as a module-level banner comment, with a correctly marked
# sibling test. The banner is prose: only a marker binds, so the test it was
# meant for is answered by nobody, and the advisory names the banner.
import pytest


# ---------------------------------------------------------------------------
# TC-001: Warning default
# ---------------------------------------------------------------------------


def test_defaults_every_finding_to_warning():
    assert 1 + 1 == 2


@pytest.mark.trace("TC-002")
def test_names_the_declaration_on_every_finding():
    assert 2 + 2 == 4
