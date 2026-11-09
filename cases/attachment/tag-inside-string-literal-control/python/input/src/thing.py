"""The control: the same two tests, and the tag is a marker."""


@pytest.mark.trace("TC-001")
def test_real():
    assert True


@pytest.mark.trace("TC-002")
def test_carries_an_example():
    # ONE LINE MOVED. The id is in a marker, where it binds, and the string
    # below carries no tag-shaped text at all. So this test really does verify
    # the second row and it is backed.
    example = """
        an ordinary fixture string
    """
    assert "ordinary" in example
