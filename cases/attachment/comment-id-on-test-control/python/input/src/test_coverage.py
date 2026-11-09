import pytest


@pytest.mark.trace("TC-002")
def test_marked():
    assert 2 + 2 == 4


@pytest.mark.trace("TC-001")
def test_commented():
    assert 1 + 1 == 2
