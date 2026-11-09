import pytest


@pytest.mark.trace("TC-002")
def test_marked():
    assert 2 + 2 == 4


# TC-001: this comment names the row, but only a marker binds.
def test_commented():
    assert 1 + 1 == 2
