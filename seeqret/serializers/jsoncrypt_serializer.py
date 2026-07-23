import json

from .serializer import BaseSerializer, serializer
from ..models import jason
from ..models.secret import Secret, hash_secrets


@serializer
class JsonCryptSerializer(BaseSerializer):
    """Asymmetrically encrypted JSON export (NaCl Box per value).
    """
    version = 1
    tag = 'json-crypt'

    def to_json_object(self, secrets):
        res = {
            "version": self.version,
            "from": self.sender,
            "to": self.receiver,
            "secrets": [s.encrypt_to_dict(
                self.sender_private_key,
                self.receiver_public_key
            ) for s in secrets],
            "signature": hash_secrets(secrets),
        }
        return res

    def dumps(self, secrets, system):
        return jason.dumps(self.to_json_object(secrets), indent=4)

    def loads(self, text):
        return text

    def load(self, text):
        """Decrypt an export produced by ``dumps`` (ours or
           jseeqret's -- the formats are identical). Requires
           ``sender`` (for the public key that authenticates the
           ciphertext) and ``receiver_private_key``.
        """
        data = json.loads(text)
        res = []
        for s in data['secrets']:
            plaintext = Secret.decrypt_value(
                s['value'],
                self.sender_public_key,
                self.receiver_private_key,
            ).decode('utf-8')
            res.append(Secret(
                app=s['app'],
                env=s['env'],
                key=s['key'],
                type=s.get('type') or 'str',
                plaintext_value=plaintext,
                # Sender's modification time (v006 exports); None from
                # older tools. Advisory import metadata.
                updated_at=s.get('updated_at'),
            ))
        return res
