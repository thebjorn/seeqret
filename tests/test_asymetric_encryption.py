
from seeqret.seeqrypt.nacl_backend import (
    generate_private_key,
    asymetric_encrypt_string, asymetric_decrypt_string,
)


def test_asymetric_roundtrip():
    message = 'hello world'

    A = generate_private_key()
    A_public = A.public_key
    # print()
    # print('A_private:', encoding.Base64Encoder.encode(A._private_key))
    # print('A_public:', encoding.Base64Encoder.encode(bytes(A_public)))
    B = generate_private_key()
    B_public = B.public_key
    # print('B_public:', encoding.Base64Encoder.encode(bytes(B_public)))

    ciphertext = asymetric_encrypt_string(message, A, B_public)
    assert message == asymetric_decrypt_string(ciphertext, B, A_public)
