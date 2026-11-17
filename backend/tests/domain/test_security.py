from app.domain.security import hash_password, verify_password


def test_verify_password_succeeds_for_the_correct_password():
    hashed = hash_password("correct horse battery staple")

    assert verify_password("correct horse battery staple", hashed)


def test_verify_password_fails_for_the_wrong_password():
    hashed = hash_password("correct horse battery staple")

    assert not verify_password("wrong password", hashed)


def test_hash_password_salts_so_the_same_password_hashes_differently():
    assert hash_password("same password") != hash_password("same password")
