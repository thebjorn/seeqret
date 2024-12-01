import gnupg

PASSPHRASE = 'correct horse battery staple'


def generate_keys(gpg, user):
    # gpg = gnupg.GPG(gnupghome=f'{user}/.gnupg')
    key = gpg.gen_key(
        gpg.gen_key_input(
            key_type="RSA", 
            key_length=4096,
            name_email=f'{user}@example.com',
            passphrase=PASSPHRASE
        ))

    with open(f'{user}/.gnupg/gpg-public.asc', 'w') as f:
        pubkey = gpg.export_keys(key.fingerprint)
        print(pubkey.replace('\r', ''), file=f)

    with open(f'{user}/.gnupg/gpg-private.asc', 'w') as f:
        privkey = gpg.export_keys(key.fingerprint, secret=True, 
                                  passphrase=PASSPHRASE)
        print(privkey.replace('\r', ''), file=f)


def encrypt_file(sender, file_name, recipient, suffix='.pgp-enc'):
    gpg = gnupg.GPG(gnupghome=f'{sender}/.gnupg')
    with open(file_name, 'rb') as f:
        plaintext = f.read()

    ciphertext = gpg.encrypt(plaintext, recipients=[recipient])

    with open(file_name + suffix, 'w') as f:
        print(str(ciphertext).replace('\r', ''), file=f)


def decrypt_file(file_name, recipient):
    gpg = gnupg.GPG(gnupghome=f'{recipient}/.gnupg')
    with open(file_name, 'rb') as f:
        ciphertext = f.read()

    tmp = gpg.decrypt(ciphertext, passphrase=PASSPHRASE)
    return tmp.data


def setup_gpg(user):
    os.makedirs(f'{user}/.gnupg', exist_ok=True)
    gpg = gnupg.GPG(gnupghome=f'{user}/.gnupg')
    generate_keys(gpg, user)


def import_key(user, pubkey):
    gpg = gnupg.GPG(gnupghome=f'{user}/.gnupg')
    tmp = gpg.import_keys(pubkey)
    gpg.trust_keys(tmp.fingerprints, 'TRUST_ULTIMATE')


if __name__ == '__main__':
    import os

    plaintext = open('test.txt', 'rb').read()

    # generate public/private keys for andy and bob
    setup_gpg('andy')
    setup_gpg('bob')

    # import each other's public keys
    andy_pubkey = open('andy/.gnupg/gpg-public.asc').read()
    bob_pubkey = open('bob/.gnupg/gpg-public.asc').read()

    # keys must be imported to be able to encrypt messages to the person
    import_key('andy', bob_pubkey)
    import_key('bob', andy_pubkey)

    # the email is from setup_gpg -> generate_keys -> name_email
    encrypt_file('bob', 'test.txt', 'andy@example.com', suffix='.bob2andy')
    pt = decrypt_file('test.txt.bob2andy', 'andy')
    # print("PT:", repr(pt), repr(plaintext))
    assert plaintext == pt
