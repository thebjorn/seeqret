from .serializer import BaseSerializer, serializer
from ..models import jason
from ..models.secret import hash_secrets


@serializer
class JsonCryptSerializer(BaseSerializer):
    """Help text jsoncrypt.
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
