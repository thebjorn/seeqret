# code from https://www.youtube.com/watch?v=bd5nsMscPo0&t=4s and copilot

import rsa
from cryptography.fernet import Fernet


def generate_keys():
    key = Fernet.generate_key()

    with open('symetric.key', 'wb') as f:
        f.write(key)

    public_key, private_key = rsa.newkeys(2048)
    with open('public.key', 'wb') as f:
        f.write(public_key.save_pkcs1('PEM'))

    with open('private.key', 'wb') as f:
        f.write(private_key.save_pkcs1('PEM'))


def encrypt_file(file_name, suffix='.enc'):
    with open('public.key', 'rb') as f:
        public_key = rsa.PublicKey.load_pkcs1(f.read())

    with open(file_name, 'rb') as f:
        data = f.read()

    encrypted_data = rsa.encrypt(data, public_key)

    with open(file_name + suffix, 'wb') as f:
        f.write(encrypted_data)


def decrypt_file(file_name):
    with open('private.key', 'rb') as f:
        private_key = rsa.PrivateKey.load_pkcs1(f.read())

    with open(file_name, 'rb') as f:
        data = f.read()

    decrypted_data = rsa.decrypt(data, private_key)

    with open(file_name + '.dec', 'wb') as f:
        f.write(decrypted_data)

    return decrypted_data


def encrypt_file_symetric(file_name, suffix='.enc'):
    with open('symetric.key', 'rb') as f:
        key = f.read()

    cipher = Fernet(key)

    with open(file_name, 'rb') as f:
        data = f.read()

    encrypted_data = cipher.encrypt(data)

    with open(file_name + suffix, 'wb') as f:
        f.write(encrypted_data)


def decrypt_file_symetric(file_name):
    with open('symetric.key', 'rb') as f:
        key = f.read()

    cipher = Fernet(key)

    with open(file_name, 'rb') as f:
        data = f.read()

    decrypted_data = cipher.decrypt(data)

    with open(file_name + '.dec', 'wb') as f:
        f.write(decrypted_data)

    return decrypted_data


if __name__ == '__main__':
    plaintext = open('test.txt', 'rb').read()
    # generate_keys()
    encrypt_file('test.txt', '.asymetric')
    assert plaintext == decrypt_file('test.txt.asymetric')
    encrypt_file_symetric('test.txt', '.symetric')
    assert plaintext == decrypt_file_symetric('test.txt.symetric')
