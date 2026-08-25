# A real, correctly-tagged test. The tag is not the defect.

import pytest


class TestCoverage:
    @pytest.mark.trace("TC-001")
    def test_covers_the_criterion(self):
        assert 1 + 1 == 2
