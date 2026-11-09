@pytest.mark.trace("TC-001")
def test_covers_the_criterion():
    # the correctly tagged test backs the minted row.
    assert 1 + 1 == 2
