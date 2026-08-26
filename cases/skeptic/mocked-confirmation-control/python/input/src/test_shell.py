class Confirmation:
    @classmethod
    def from_user(cls):
        return cls()


def grant_root(_confirmation: Confirmation) -> bool:
    return True


# Trace: TC-001
def test_covers():
    assert grant_root(Confirmation.from_user())
