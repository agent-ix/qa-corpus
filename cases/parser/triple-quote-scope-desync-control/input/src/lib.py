# The same shape with the DECLARED marker, and a genuine docstring beside it.
#
# Two properties in one control, because the fix for the embedded-string case
# must not break the ordinary one:
#
#   * `_documented` carries a plain method docstring — string body, never code;
#   * `_fixture` embeds a triple-quoted literal holding a class at column 0.
#
# Both are string bodies. Neither may reach the scope stack, so the test after
# them is still a method of `TestCoverage` and its declared marker binds.

import pytest


class TestCoverage:
    def _documented(self):
        """An ordinary docstring, and nothing in it is code."""
        return None

    def _fixture(self):
        source = """
class Settings(BaseSettings):
    field: str = "value"
"""
        return source

    @pytest.mark.trace("TC-001")
    def test_covers_the_criterion(self):
        assert 1 + 1 == 2
