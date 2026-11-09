import pytest


@pytest.mark.trace("TC-001")
def test_backed_and_commented():
    assert 1 + 1 == 2
