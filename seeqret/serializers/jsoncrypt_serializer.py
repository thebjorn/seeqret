from .serializer import BaseSerializer
from ..seeqrypt.nacl_backend import hash_message


class JsonCryptSerializer(BaseSerializer):
    def __init__(self, sender, receiver,
                 sender_private_key, receiver_public_key):
        self.sender = sender
        self.receiver = receiver
        self.sender_private_key = sender_private_key
        self.receiver_public_key = receiver_public_key

    def dumps(self, data):
        def dump_secret(secret):
            return {
                "app": secret.app,
                "env": secret.env,
                "key": secret.key,
                "val": secret.encrypt_value(self.sender_private_key,
                                            self.receiver_public_key),
                "typ": secret.type,
            }

        # noinspection PyDictCreation
        res = {
            "from": self.sender,
            "to": self.receiver,
            "data": [dump_secret(s) for s in data]
        }
        res['signature'] = hash_message(
            "\n".join(repr(s) for s in data).encode("utf8")
        )
        return res

    def serialize_version(self, version, obj):
        return obj

    def deserialize_version(self, version, obj):
        return obj
