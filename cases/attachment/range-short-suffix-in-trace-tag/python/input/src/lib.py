"""A short-suffix range inside a trace tag binds no id at all (CR-187)."""

import pytest


class TestCoverage:
    @pytest.mark.trace("FR-001-AC-1..2")
    def test_covers_the_range(self):
        assert 1 + 1 == 2
