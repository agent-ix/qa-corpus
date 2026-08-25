"""The same tree with the DECLARED marker: `@pytest.mark.trace`."""

import pytest


class TestCoverage:
    @pytest.mark.trace("TC-001")
    def test_covers_the_criterion(self):
        assert 1 + 1 == 2
