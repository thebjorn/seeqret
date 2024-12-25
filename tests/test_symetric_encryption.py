import pytest

from seeqret.seeqrypt.aes_fernet import encrypt_string, decrypt_string
from seeqret.seeqrypt.utils import format_encrypted_data, get_or_create_symetric_key
from seeqret.fileutils import remove_file_if_exists

COUNTER = 0


@pytest.fixture
def symetric_key():
    global COUNTER
    COUNTER += 1
    name = f'symetric-{COUNTER}.key'
    yield get_or_create_symetric_key(name)
    remove_file_if_exists(name)


def test_aes_fernet_roundtrip(symetric_key):
    print()
    plaintext = b"Hello, World! lorem ipsum dolor sit ametHello, World! lorem ipsum dolor sit ametHello, World! lorem ipsum dolor sit ametHello, World! lorem ipsum dolor sit ametHello, World! lorem ipsum dolor sit ametHello, World! lorem ipsum dolor sit ametHello, World! lorem ipsum dolor sit ametHello, World! lorem ipsum dolor sit ametHello, World! lorem ipsum dolor sit ametHello, World! lorem ipsum dolor sit ametHello, World! lorem ipsum dolor sit ametHello, World! lorem ipsum dolor sit ametHello, World! lorem ipsum dolor sit ametHello, World! lorem ipsum dolor sit ametHello, World! lorem ipsum dolor sit ametHello, World! lorem ipsum dolor sit ametHello, World! lorem ipsum dolor sit amet"
    encrypted = encrypt_string(symetric_key, plaintext)
    print("ENCRYPTED:", len(encrypted))
    print(format_encrypted_data(encrypted))
    decrypted = decrypt_string(symetric_key, encrypted)
    print("DECRYPTED:", len(decrypted), decrypted)
    assert plaintext == decrypted
