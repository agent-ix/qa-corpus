"""Seeded: a legacy trace form inside a string literal, in a test's own span."""


def test_real():
    # Trace: TC-001
    assert True


def test_carries_an_example():
    # THE DEFECT. The legacy textual form below is DATA this test asserts
    # about, not a tag on this test. Rust masks string contents before matching
    # legacy forms; Python did not, so `TC-002` bound here and the row read as
    # verified by a test that never touches it.
    example = """
        Trace: TC-002
    """
    assert "Trace" in example
