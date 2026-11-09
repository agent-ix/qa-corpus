"""Seeded: comment-shaped text inside a string literal on a test's own declaration."""

import pytest


@pytest.mark.trace("TC-001")
def test_real():
    assert True


@pytest.mark.skip(reason="# TC-002: not a tag")
def test_carries_an_example():
    assert True
