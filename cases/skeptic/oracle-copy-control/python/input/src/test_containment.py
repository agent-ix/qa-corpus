def is_contained(path: str) -> bool:
    return not path.startswith("/") and ".." not in path and "\0" not in path


# Trace: TC-001
def test_covers():
    path = "a/b"
    expected = True
    assert is_contained(path) == expected
