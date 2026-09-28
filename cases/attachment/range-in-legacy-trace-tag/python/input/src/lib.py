"""A range in a legacy `Trace:` line binds no id, not even its left endpoint (CR-187)."""


class TestCoverage:
    def test_covers_the_range(self):
        # Trace: FR-001-AC-1..FR-001-AC-2
        assert 1 + 1 == 2
