from seeqret.seeqrypt.aes_fernet import encrypt_string, decrypt_string
from seeqret.seeqrypt.utils import format_encrypted_data


def test_aes_fernet_roundtrip():
    from seeqret.seeqrypt.utils import get_or_create_symetric_key
    print()
    key = get_or_create_symetric_key('symetric.key')
    plaintext = b"Hello, World! lorem ipsum dolor sit ametHello, World! lorem ipsum dolor sit ametHello, World! lorem ipsum dolor sit ametHello, World! lorem ipsum dolor sit ametHello, World! lorem ipsum dolor sit ametHello, World! lorem ipsum dolor sit ametHello, World! lorem ipsum dolor sit ametHello, World! lorem ipsum dolor sit ametHello, World! lorem ipsum dolor sit ametHello, World! lorem ipsum dolor sit ametHello, World! lorem ipsum dolor sit ametHello, World! lorem ipsum dolor sit ametHello, World! lorem ipsum dolor sit ametHello, World! lorem ipsum dolor sit ametHello, World! lorem ipsum dolor sit ametHello, World! lorem ipsum dolor sit ametHello, World! lorem ipsum dolor sit amet"
    encrypted = encrypt_string(key, plaintext)
    print("ENCRYPTED:", len(encrypted))
    print(format_encrypted_data(encrypted))
    decrypted = decrypt_string(key, encrypted)
    print("DECRYPTED:", len(decrypted), decrypted)
    assert plaintext == decrypted
