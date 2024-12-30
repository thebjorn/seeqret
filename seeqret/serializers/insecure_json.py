from ..models.jason import dumps, loads
from .serializer import BaseSerializer, ValidationError


class InsecureJsonSerializer(BaseSerializer):
    def __init__(self):
        super().__init__()

    def serialize_version(self, version, storage):
        data = {
            "serializer": {
                "name": "insecure_json",
                "version": version,
            },
            "storage": {
                "name": storage.name,
                "version": storage.version,
            },
            "data": {
                "users": storage.fetch_users(),
                "secrets": storage.fetch_secrets(),
            }
        }
        return dumps(data)

    def deserialize_version(self, version, data):
        tmp = loads(data)
        if tmp["serializer"]["version"] != version:
            # XXX: for now, bail if incorrect version
            raise ValidationError("Incorrect version")
        return tmp["data"]
