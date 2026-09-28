"""The control for `range-in-legacy-trace-tag`: the same ids as a legacy list."""


class TestCoverage:
    def test_covers_the_list(self):
        # Trace: FR-001-AC-1, FR-001-AC-2
        assert 1 + 1 == 2
