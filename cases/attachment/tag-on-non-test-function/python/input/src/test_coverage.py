# The correct half of the MIXED pair: one real test, tagged on the test itself.
# It binds, so the census reads 1 candidate / 1 bound — a clean 100% — while the
# row the production tag names goes unbacked.
from coverage import normalize_severity


# TC-002: on the test, which registers an evidence symbol.
def test_names_the_declaration_on_every_finding():
    assert normalize_severity({}) == "warning"
