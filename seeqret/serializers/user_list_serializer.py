"""Encrypted user-list exchange format (mirrors jseeqret).

   Used by the onboarding flow to introduce teammates to each other:
   the whole record list is encrypted as a single NaCl Box so a
   Slack observer learns nothing about team membership.
"""
import json

from .serializer import BaseSerializer, serializer, ValidationError
from ..seeqrypt.nacl_backend import (
    asymetric_decrypt_string,
    asymetric_encrypt_string,
    fingerprint,
)


@serializer
class UserListSerializer(BaseSerializer):
    """Payload shape::

           {"version": 1, "from": "<username>", "to": "<username>",
            "users": "<naclb64 of the records json>",
            "signature": "<5-char fingerprint of the ciphertext>"}

       where records is ``[{username, email, pubkey, name}]``.
    """
    version = 1
    tag = 'user-list'

    def dumps(self, users, system=None):
        records = [dict(
            username=u.username,
            email=u.email,
            pubkey=u.pubkey,
            name=u.name,
        ) for u in users]
        encrypted = asymetric_encrypt_string(
            json.dumps(records, separators=(',', ':')),
            self.sender_private_key,
            self.receiver_public_key,
        )
        return json.dumps({
            "version": self.version,
            "from": self.sender.username,
            "to": self.receiver.username,
            "users": encrypted,
            "signature": fingerprint(encrypted.encode('utf-8')),
        }, indent=2)

    def load(self, text: str) -> list[dict]:
        """Decrypt a user-list payload into plain record dicts.

           Accepts the payload text or an already-parsed dict.
        """
        data = json.loads(text) if isinstance(text, str) else text
        if data.get('version') != self.version:
            raise ValidationError(
                f"version mismatch, found {data.get('version')}"
                f" - expected {self.version}")
        plaintext = asymetric_decrypt_string(
            data['users'],
            self.receiver_private_key,
            self.sender_public_key,
        )
        return json.loads(plaintext)
