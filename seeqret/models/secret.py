from ..seeqrypt.aes_fernet import decrypt_string
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
        self.app = app
        self.env = env
        self.key = key
        self._value = value
        self.type = type

    def __str__(self):
        return (f'Secret({self.app}, {self.env}, '
                f'{self.key}, {self.value}, {self.type})')

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

    @property
    def row(self):
        return [
            self.app,
            self.env,
            self.key,
            self.value,
            self.type
        ]
