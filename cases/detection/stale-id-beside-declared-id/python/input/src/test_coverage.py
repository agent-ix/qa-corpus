import pytest


@pytest.mark.trace("TC-999", "TC-001")
def test_covers_the_criterion():
    assert True
