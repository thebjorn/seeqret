from ..seeqrypt.aes_fernet import decrypt_string
from ..seeqrypt.nacl_backend import (
    asymetric_encrypt_string,
    hash_message,
    fingerprint,
    asymetric_decrypt_string,
)
from ..seeqrypt.utils import load_symetric_key
import logging

logger = logging.getLogger(__name__)


def cnvt(typename, val):
    cfns = {
        'str': str,
        'int': int,
    }
    ident = lambda x: x     # noqa
    return cfns.get(typename, ident)(val)


class Secret:
    def __init__(self, app: str, env: str, key: str, value: bytes, type: str):
        self.app: str = app
        self.env: str = env
        self.key: str = key
        self._value = value
        self.type = type

    def __str__(self):
        return (f'Secret({self.app}, {self.env}, '
                f'{self.key}, {self.value}, {self.type})')

    def __repr__(self):
        return f'{self.app}:{self.env}:{self.key}:{self.type}:{self.value}'

    def __json__(self):
        return dict(
            app=self.app,
            env=self.env,
            key=self.key,
            value=self._value,
            type=self.type,
        )

    @property
    def value(self):
        cipher = load_symetric_key('seeqret.key')
        # logger.debug('decrypting: %s %s', self._value, type(self._value))
        val = decrypt_string(cipher, self._value).decode('utf-8')
        return cnvt(self.type, val)

    def encrypt_value(self, sender_private_key, receiver_pubkey):
        return asymetric_encrypt_string(
            self.value, sender_private_key, receiver_pubkey
        )

    @staticmethod
    def decrypt_value(cipher,
                      sender_public_key,
                      receiver_private_key) -> bytes:
        print("CIPHER:", cipher)
        # import base64
        # print(base64.b64decode(cipher))
        return asymetric_decrypt_string(
            cipher, receiver_private_key, sender_public_key
        ).encode('utf-8')

    def fingerprint(self):
        txt = f'{self.app}:{self.env}:{self.key}:{self.type}:{self.value}'
        return fingerprint(txt.encode('utf-8'))

    def encrypt_to_string(self, sender_private_key, receiver_pubkey):
        f = self.fingerprint()
        v = self.encrypt_value(sender_private_key, receiver_pubkey)
        return f'{f}:{self.app}:{self.env}:{self.key}:{self.type}:{v}'

    def encrypt_to_dict(self, sender_private_key, receiver_pubkey):
        return dict(
            app=self.app,
            env=self.env,
            key=self.key,
            value=self.encrypt_value(sender_private_key, receiver_pubkey),
            type=self.type,
        )

    @property
    def row(self):
        return [
            self.app,
            self.env,
            self.key,
            self.value,
            self.type
        ]


def _secrets_to_text(secrets: list[Secret]) -> str:
    txt = ''
    for s in sorted(secrets, key=lambda s: (s.app, s.env, s.key)):
        txt += f'{s.app}:{s.env}:{s.key}:{s.type}:{s.value}\n'
    return txt


def hash_secrets(secrets: list[Secret]) -> str:
    return hash_message(_secrets_to_text(secrets).encode('utf-8'))


def fingerprint_secrets(secrets: list[Secret]) -> str:
    return fingerprint(_secrets_to_text(secrets).encode('utf-8'))
