"""Real test, plausible marker spelling, undeclared form."""

import pytest


class TestCoverage:
    @pytest.mark.tracks("TC-001")
    def test_covers_the_criterion(self):
        assert 1 + 1 == 2
