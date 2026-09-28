"""A range across two requirements' ids binds no id at all (CR-187)."""

import pytest


class TestCoverage:
    @pytest.mark.trace("FR-001-AC-2..FR-002-AC-1")
    def test_covers_the_range(self):
        assert 1 + 1 == 2
