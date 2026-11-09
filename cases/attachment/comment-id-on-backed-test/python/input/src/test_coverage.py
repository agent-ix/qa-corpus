import pytest


# TC-001: still a comment, though the marker below names the same id.
@pytest.mark.trace("TC-001")
def test_backed_and_commented():
    assert 1 + 1 == 2
