import os

from cryptography.fernet import Fernet

from seeqret.seeqrypt.aes_fernet import encrypt_string, decrypt_string
from seeqret.seeqrypt.utils import (
    _chunks,
    format_encrypted_data,
    generate_symetric_key,
    load_symetric_key,
    get_or_create_symetric_key,
    generate_symetric_key,
    # generate_asymetric_keys,
    # load_public_key,
    # load_private_key,
)


def test_chunks():
    assert list(_chunks([1, 2, 3, 4, 5], 2)) == [[1, 2], [3, 4], [5]]


def test_format_encrypted_data():
    fmt = format_encrypted_data(b'0123456789'*10).splitlines()
    assert len(fmt) == 2
    assert len(fmt[0]) == 64
    assert len(fmt[1]) == 100 % 64


def test_generate_symetric_key():
    key = generate_symetric_key('test_generate_symetric_key.key')
    assert isinstance(key, Fernet)
    assert os.path.exists('test_generate_symetric_key.key')
    os.unlink('test_generate_symetric_key.key')


def test_load_symetric_key():
    key = generate_symetric_key('test_load_symetric_key.key')
    k2 = load_symetric_key('test_load_symetric_key.key')
    msg = b'hello world'
    assert decrypt_string(k2, encrypt_string(key, msg)) == msg
    os.unlink('test_load_symetric_key.key')


def test_get_or_create_symetric_key():
    key = get_or_create_symetric_key('test_get_or_create_symetric_key.key')
    k2 = get_or_create_symetric_key('test_get_or_create_symetric_key.key')
    msg = b'hello world'
    assert decrypt_string(k2, encrypt_string(key, msg)) == msg
    os.unlink('test_get_or_create_symetric_key.key')
#
#
# def test_load_public_key():
#     _pub, priv = generate_asymetric_keys('test_load_public_key.key')
#     pub = load_public_key('test_load_public_key.key')
#
#
#
# def test_load_private_key():
#     assert load_private_key() == b'12345'
