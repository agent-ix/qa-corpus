# A test class whose helper embeds a fixture holding a class at column 0.
#
# `source = ` followed by the opening delimiter does not START the line with
# it, so a scanner that tracks triple quotes only at the start of a line never
# enters string mode. The CLOSING delimiter does start its line, and is then
# read as an opening one: from there the state is inverted and the embedded
# `class Settings` is parsed as real code, popping `TestCoverage` off the scope
# stack. Every method after it is classified `Function` rather than
# `TestFunction`, so it is not an evidence candidate and its tag binds nothing.
#
# The marker below spells `tracks`, which the module never declares, so the
# symbol is a CANDIDATE THAT BINDS NOTHING — that is the seeded defect. A
# parser that cannot see the symbol at all reports neither the symbol nor the
# defect, and a corpus that looks clean because nothing was read is the exact
# failure this corpus exists to catch.

import pytest


class TestCoverage:
    def _fixture(self):
        source = """
class Settings(BaseSettings):
    field: str = "value"
"""
        return source

    @pytest.mark.tracks("TC-001")
    def test_covers_the_criterion(self):
        assert 1 + 1 == 2
