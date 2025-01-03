from ..models import jason
from ..models.jason import loads
from .serializer import BaseSerializer, ValidationError, serializer
from ..models.secret import hash_secrets, Secret


@serializer
class InsecureJsonSerializer(BaseSerializer):
    """For debugging (and maybe backup?)
    """
    version = 1
    tag = 'backup'

    def to_json_object(self, secrets):
        res = {
            "version": self.version,
            "from": self.sender,
            "to": self.receiver,
            "secrets": [s.to_plaintext_dict() for s in secrets],
            "signature": hash_secrets(secrets),
        }
        return res

    def dumps(self, secrets, system):
        return jason.dumps(self.to_json_object(secrets))

    def deserialize_version(self, text):
        tmp = loads(text)
        if tmp["version"] != self.version:
            # XXX: for now, bail if incorrect version
            raise ValidationError("Incorrect version")
        return [Secret(**s) for s in tmp["secrets"]]
