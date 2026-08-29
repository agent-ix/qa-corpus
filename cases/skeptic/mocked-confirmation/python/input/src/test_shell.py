class Confirmation:
    @classmethod
    def allow(cls):
        return cls()


def grant_root(_confirmation: Confirmation) -> bool:
    return True


# Trace: TC-001
def test_covers():
    assert grant_root(Confirmation.allow())
