"""The control for `range-in-trace-tag`: each id tagged separately."""

import pytest


class TestCoverage:
    @pytest.mark.trace("TC-001", "FR-001-AC-1")
    def test_covers_ac1(self):
        assert 1 + 1 == 2

    @pytest.mark.trace("TC-002", "FR-001-AC-2")
    def test_covers_ac2(self):
        assert 1 + 1 == 2
