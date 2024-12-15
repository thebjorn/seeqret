from binascii import b2a_base64

from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes


def asymetric_encrypt_string(public_key, original_text: bytes) -> bytes:
    """Encrypt a string using RSA asymmetric encryption.

       Args:
           public_key: The public key.
           original_text: The string to encrypt.

       Returns:
           The encrypted string.

       Usage:
           from utils import load_public_key
           public_key = load_public_key('public.pem')
           encrypted = encrypt_string(public_key, b"Hello, World!")

    """
    return b2a_base64(public_key.encrypt(
        original_text,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    ))


def asymetric_decrypt_string(private_key, encrypted_text: bytes) -> bytes:
    """Decrypt a string using RSA asymmetric encryption.

       Args:
           private_key: The private key.
           encrypted_text: The string to decrypt.

       Returns:
           The decrypted string.

       Usage:
           from utils import load_private_key
           private_key = load_private_key('private.pem')
           decrypted = decrypt_string(private_key, encrypted)

    """
    return private_key.decrypt(
        encrypted_text,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )


def sign_string(private_key, original_text: bytes) -> bytes:
    """Sign a string using RSA asymmetric encryption.

       Args:
           private_key: The private key.
           original_text: The string to sign.

       Returns:
           The signed string.

       Usage:
           from utils import load_private_key
           private_key = load_private_key('private.pem')
           signed = sign_string(private_key, b"Hello, World!")

    """
    return b2a_base64(private_key.sign(
        original_text,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    ))
