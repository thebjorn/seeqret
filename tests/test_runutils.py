from seeqret.run_utils import current_user


def test_current_user():
    print("CURRENT:USER:", current_user)
    assert current_user()
