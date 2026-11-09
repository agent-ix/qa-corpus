"""Seeded: tag-shaped text inside a string literal, in a test's own span."""


@pytest.mark.trace("TC-001")
def test_real():
    assert True


def test_carries_an_example():
    # THE DEFECT SHAPE. The text below is DATA this test asserts about, not a
    # tag on this test: no id in it binds, and none is reported as a misplaced
    # citation, because a string literal is not an annotation.
    example = """
        Trace: TC-002
    """
    assert "Trace" in example
