"""The control: the same two tests, and the second names its row in a marker."""

import pytest


@pytest.mark.trace("TC-001")
def test_real():
    assert True


@pytest.mark.trace("TC-002")
@pytest.mark.skip(reason="an ordinary reason")
def test_carries_an_example():
    assert True
