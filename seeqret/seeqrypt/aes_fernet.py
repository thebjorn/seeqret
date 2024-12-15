

def encrypt_string(key, original_text: bytes) -> bytes:
    """Encrypt a string using Fernet symmetric encryption.

       Args:
           key: The encryption key.
           original_text: The string to encrypt.

       Returns:
           The encrypted string.

       Usage:
           from utils import get_or_create_symetric_key
           key = get_or_create_symetric_key('symetric.key')
           encrypted = encrypt_string(key, b"Hello, World!")

    """
    return key.encrypt(original_text)


def decrypt_string(key, encrypted_text: bytes) -> bytes:
    """Decrypt a string using Fernet symmetric encryption.

       Args:
           key: The encryption key.
           encrypted_text: The string to decrypt.

       Returns:
           The decrypted string.

       Usage:
           from utils import get_or_create_symetric_key
           key = get_or_create_symetric_key('symetric.key')
           decrypted = decrypt_string(key, encrypted)
    """
    return key.decrypt(encrypted_text)
