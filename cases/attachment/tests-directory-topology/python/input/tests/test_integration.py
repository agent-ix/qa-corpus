import pytest


@pytest.mark.trace("TC-001")
def test_covers_the_criterion_from_a_tests_directory():
    assert 1 + 1 == 2
