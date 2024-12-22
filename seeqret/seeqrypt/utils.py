from cryptography.fernet import Fernet


def _chunks(data, size):
    for i in range(0, len(data), size):
        yield data[i:i + size]


def format_encrypted_data(data):
    res = ''
    for i in _chunks(data.decode(), 64):
        res += i + '\n'
    return res


def generate_symetric_key(fname=None):
    key = Fernet.generate_key()
    if fname:
        with open(fname, 'wb') as f:
            f.write(key)
    return Fernet(key)


def load_symetric_key(fname):
    with open(fname, 'rb') as f:
        key = f.read()
        return Fernet(key)


def get_or_create_symetric_key(fname):
    try:
        return load_symetric_key(fname)
    except FileNotFoundError:
        return generate_symetric_key(fname)


# def generate_asymetric_keys(public_fname=None, private_fname=None):
#     public_key, private_key = rsa.newkeys(2048)
#
#     if public_fname:
#         with open(public_fname, 'wb') as f:
#             f.write(public_key.save_pkcs1('PEM'))
#
#     if private_fname:
#         with open(private_fname, 'wb') as f:
#             f.write(private_key.save_pkcs1('PEM'))
#
#     return public_key, private_key
#
#
# def load_public_key(fname):
#     with open(fname, 'rb') as f:
#         public_key = rsa.PublicKey.load_pkcs1(f.read())
#         return public_key
#
#
# def load_private_key(fname):
#     with open(fname, 'rb') as f:
#         private_key = rsa.PrivateKey.load_pkcs1(f.read())
#         return private_key
