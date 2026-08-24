"""A real, correctly-tagged pytest test. The tag is not the defect."""

import pytest


@pytest.mark.trace("TC-001")
def test_covers_the_criterion():
    assert 1 + 1 == 2
