from nacl.hash import sha256
from nacl.public import PrivateKey, Box, PublicKey
from nacl import encoding
from nacl.signing import SigningKey

from seeqret.fileutils import write_binary_file, read_binary_file


def generate_private_key(fname=None) -> PrivateKey:
    pkey = PrivateKey.generate()
    if fname:
        write_binary_file(
            fname,
            encoding.Base64Encoder.encode(pkey._private_key),
        )
    return pkey


def private_key(string: bytes) -> PrivateKey:
    """Bytes to private key.
    """
    return PrivateKey(string, encoder=encoding.Base64Encoder)


def public_key(string: str | bytes) -> PublicKey:
    """Bytes to public key.
    """
    if isinstance(string, str):
        string = string.encode('ascii')
    return PublicKey(string, encoder=encoding.Base64Encoder)


def load_private_key(fname: str) -> PrivateKey:
    """Load private key from file.
    """
    return private_key(read_binary_file(fname))


def load_public_key(fname: str) -> PublicKey:
    """Load public key from file.
    """
    return public_key(read_binary_file(fname))


def save_public_key(fname: str, pkey: PrivateKey) -> bytes:
    pubkey = encoding.Base64Encoder.encode(bytes(pkey.public_key))
    write_binary_file(fname, pubkey)
    return pubkey


def save_private_key(fname: str, pkey: PrivateKey) -> bytes:
    pkey = encoding.Base64Encoder.encode(bytes(pkey._private_key))
    write_binary_file(fname, pkey)
    return pkey


def asymetric_encrypt_string(string: str,
                             sender_private_key: PrivateKey,
                             recipient_public_key: PublicKey) -> str:
    box = Box(
        private_key=sender_private_key,
        public_key=recipient_public_key
    )
    val = string.encode('utf-8')
    return encoding.Base64Encoder.encode(box.encrypt(val)).decode('ascii')


def asymetric_decrypt_string(string: str,
                             receiver_private_key: PrivateKey,
                             sender_public_key: PublicKey) -> str:
    box = Box(
        private_key=receiver_private_key,
        public_key=sender_public_key
    )
    val = string.encode('ascii')
    return box.decrypt(encoding.Base64Encoder.decode(val)).decode('ascii')


def sign_message(string: bytes):
    signing_key = SigningKey.generate()
    signed = signing_key.sign(string)
    verify_key = signing_key.verify_key
    verify_key_bytes = verify_key.encode()
    return verify_key_bytes, signed


def hash_message(string: bytes, encoder=encoding.HexEncoder) -> str:
    return sha256(string, encoder=encoding.HexEncoder).decode('ascii')
    # return sha256(string, encoder=encoding.Base64Encoder).decode('ascii')


def fingerprint(string: bytes) -> str:
    res = hash_message(string, encoder=encoding.HexEncoder)
    return res[-5:]
