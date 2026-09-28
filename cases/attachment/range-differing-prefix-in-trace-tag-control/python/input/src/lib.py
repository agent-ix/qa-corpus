"""The control for `range-differing-prefix-in-trace-tag`: each id tagged separately."""

import pytest


class TestCoverage:
    @pytest.mark.trace("FR-001-AC-2")
    def test_covers_fr001_ac2(self):
        assert 1 + 1 == 2

    @pytest.mark.trace("FR-002-AC-1")
    def test_covers_fr002_ac1(self):
        assert 1 + 1 == 2
