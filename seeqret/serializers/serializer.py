"""
Base classes for the serializers.
"""
import click

SERIALIZERS = {}


class ValidationError(ValueError):
    pass


def serializer(cls):
    if not hasattr(cls, 'tag'):
        try:
            ctx = click.get_current_context()
        except RuntimeError:
            raise ValidationError('serializer requires click context')
        ctx.fail('serializer requires click context')
    SERIALIZERS[cls.tag] = cls
    return cls


class BaseSerializer:
    version = 0

    def __init__(self, sender, receiver,
                 sender_private_key=None, receiver_private_key=None):
        self.sender = sender
        self.receiver = receiver
        self.sender_private_key = sender_private_key
        self.receiver_private_key = receiver_private_key
        self.sender_public_key = sender.public_key
        self.receiver_public_key = receiver.public_key

    def dumps(self, secrets, system):
        raise NotImplementedError()

    def load(self, text):
        raise NotImplementedError()
