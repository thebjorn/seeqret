import pytest
import os
from seeqret.pgp_filecrypt import setup_gpg, import_key, encrypt_file, decrypt_file
from seeqret.utils import remove_directory, read_binary_file

CURDIR = os.path.dirname(os.path.abspath(__file__))


@pytest.mark.skip("Skip test_pgp_filecrypt")
def test_pgp_filecrypt():
    # file known to exist
    readme_path = os.path.join(CURDIR, '../README.md')
    assert os.path.exists(readme_path)
    plaintext = read_binary_file(os.path.join(CURDIR, 'data/plaintext.ini'))

    # generate public/private keys for andy and bob
    remove_directory('andy')
    setup_gpg('andy')
    remove_directory('bob')
    setup_gpg('bob')

    # import each other's public keys
    andy_pubkey = open('andy/.gnupg/gpg-public.asc').read()
    bob_pubkey = open('bob/.gnupg/gpg-public.asc').read()

    # keys must be imported to be able to encrypt messages to the person
    import_key('andy', bob_pubkey)
    import_key('bob', andy_pubkey)

    # the email is from setup_gpg -> generate_keys -> name_email
    testfile = os.path.join(CURDIR, 'data/test.txt')
    encrypt_file('bob', testfile, 'andy@example.com', suffix='.bob2andy')
    pt = decrypt_file('test.txt.bob2andy', 'andy')
    # print("PT:", repr(pt), repr(plaintext))
    assert plaintext == pt
