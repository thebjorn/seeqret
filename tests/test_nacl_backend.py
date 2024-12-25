import os

from nacl.public import PrivateKey
from seeqret.seeqrypt.nacl_backend import (
    generate_private_key,
    load_public_key,
    load_private_key,
    save_private_key,
    save_public_key,
    public_key,
    private_key,
    asymetric_decrypt_string,
    asymetric_encrypt_string,
    sign_message,
    hash_message,
)
from seeqret.fileutils import remove_file_if_exists


def test_generate_private_key():
    # Test successful private key generation
    pkey = generate_private_key('test_generate_private_key.key')
    assert pkey is not None
    assert isinstance(pkey, PrivateKey)
    assert os.path.exists('test_generate_private_key.key')
    remove_file_if_exists('test_generate_private_key.key')


def test_load_private_key():
    # Test loading a valid private key
    valid_private_key = generate_private_key()
    save_private_key('test_load_private_key.key', valid_private_key)
    pubkey = save_public_key('test_load_public_key.key', valid_private_key)
    pubkey2 = public_key(pubkey.decode('ascii'))

    priv = load_private_key('test_load_private_key.key')
    pub = load_public_key('test_load_public_key.key')

    msg = 'hello world'
    cipher = asymetric_encrypt_string(msg, priv, pub)
    plain = asymetric_decrypt_string(cipher, priv, pub)

    assert plain == msg

    remove_file_if_exists('test_load_private_key.key')
    remove_file_if_exists('test_load_public_key.key')


def test_sign_message():
    # Test signing a message
    test_private_key = generate_private_key()
    message = b"Message to sign"
    vkb, signed = sign_message(message)
    assert signed.endswith(b"Message to sign")
    # assert signed.startswith(vkb)


def test_hash_message():
    # Test hashing functionality
    message = b"Message to hash"
    h1 = hash_message(message)
    h2 = hash_message(message + b'.')
    assert h1 is not None
    assert h1 != h2
