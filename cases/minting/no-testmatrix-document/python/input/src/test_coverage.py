"""Three real, correctly-tagged pytest tests, one per matrix row. The tags are
not the defect: all three bind. Two of the rows they answer for are invisible
to the declaration, so two of these symbols back nothing at all.
"""

import pytest


@pytest.mark.trace("TC-001")
def test_covers_the_first_criterion():
    assert 1 + 1 == 2


@pytest.mark.trace("TC-002")
def test_covers_the_second_criterion():
    assert 2 + 2 == 4


@pytest.mark.trace("TC-003")
def test_covers_the_third_criterion():
    assert 3 + 3 == 6
