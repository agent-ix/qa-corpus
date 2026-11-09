import pytest


@pytest.mark.trace("TC-001")
def test_covers():
    assert parse() == 1
