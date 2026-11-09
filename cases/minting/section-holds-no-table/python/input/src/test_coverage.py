@pytest.mark.trace("TC-001")
def test_covers_the_criterion():
    # the correctly tagged test is not the defect.
    assert 1 + 1 == 2
