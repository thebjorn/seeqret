"""
Base classes for the serializers.
"""
SERIALIZER_VERSION = 2


class ValidationError(ValueError):
    pass


class BaseSerializer:
    def serialize(self, obj):
        return self.serialize_version(SERIALIZER_VERSION, obj)

    def serialize_version(self, version, obj):
        raise NotImplementedError   # pragma: no cover

    def deserialize(self, storage):
        return self.deserialize_version(SERIALIZER_VERSION, storage)

    def deserialize_version(self, version, data):
        raise NotImplementedError   # pragma: no cover
