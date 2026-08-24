# The banner shape is taken from sqlmodel-fixtures/tests/test_loader.py:49 —
# `# FR-002: Model Resolution` between two rules of dashes, at column 0, blank
# lines above and below. That file writes seven of them. The real ones carry a
# BARE requirement id, which is a second defect (`join/tag-names-bare-fr`), so
# this fixture writes a minted `TC-` id instead: exactly one thing is wrong here,
# and it is WHERE the tag sits.
#
# MIXED on purpose — one tag at module scope beside one on the test itself.
import pytest


# ---------------------------------------------------------------------------
# TC-001: Warning default
# ---------------------------------------------------------------------------
#
# The nearest enclosing symbol is the FILE's own container symbol, which
# `python.rs` emits for every module and spans line 1 to EOF. A container does
# not bind trace ids (CR-061: a `mod tests` block would otherwise inherit every
# marker nested inside it), so TC-001 is answered by nobody.


def test_defaults_every_finding_to_warning():
    assert 1 + 1 == 2


# TC-002: the same tag form, on the test itself. This one attaches, and it is
# what keeps the census above the diagnostic floor.
@pytest.mark.trace("TC-002")
def test_names_the_declaration_on_every_finding():
    assert 2 + 2 == 4
