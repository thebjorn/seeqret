import json
import os

from .serializer import BaseSerializer, serializer, ValidationError
from ..models import Secret
from ..seeqrypt.nacl_backend import fingerprint


def _compact_json(val) -> str:
    """JSON with no whitespace, matching JS ``JSON.stringify``.

       Used for the payload signature so the two tools compute the
       same value over the same bytes.
    """
    return json.dumps(val, separators=(',', ':'))


def _username_of(field) -> str | None:
    """The ``from``/``to`` fields are usernames in the jseeqret
       format; older Python exports embedded whole user objects.
       Accept both.
    """
    if isinstance(field, str):
        return field
    if isinstance(field, dict):
        return field.get('username')
    return None


@serializer
class JsonCryptSerializer(BaseSerializer):
    """NaCl-encrypted JSON exchange format (mirrors jseeqret).

       Payload shape::

           {"version": 1, "from": "<username>", "to": "<username>",
            "secrets": [{app, env, key, value: <naclb64>, type,
                         updated_at}],
            "signature": "<5-char fingerprint of the encrypted
                           secrets array (compact JSON)>"}
    """
    version = 1
    tag = 'json-crypt'

    def to_json_object(self, secrets):
        encrypted = [s.encrypt_to_dict(
            self.sender_private_key,
            self.receiver_public_key
        ) for s in secrets]
        return {
            "version": self.version,
            "from": self.sender.username,
            "to": self.receiver.username,
            "secrets": encrypted,
            "signature": fingerprint(
                _compact_json(encrypted).encode('utf-8')),
        }

    def dumps(self, secrets, system):
        return json.dumps(self.to_json_object(secrets), indent=2)

    def load(self, text: str) -> list[Secret]:
        """Decrypt an exported payload back into Secret objects.

           *text* is the payload itself, or a path to a file holding
           it (the CLI's ``-f`` flag passes a path).
        """
        if text and '{' not in text and os.path.exists(text):
            with open(text, encoding='utf-8') as f:
                text = f.read()
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise ValidationError(f'invalid json-crypt payload: {e}')

        if data.get('version') != self.version:
            raise ValidationError(
                f"version mismatch, found {data.get('version')}"
                f" - expected {self.version}")

        res = []
        for rec in data.get('secrets', []):
            plaintext = Secret.decrypt_value(
                rec['value'],
                self.sender_public_key,
                self.receiver_private_key,
            ).decode('utf-8')
            res.append(Secret(
                app=rec['app'],
                env=rec['env'],
                key=rec['key'],
                plaintext_value=plaintext,
                type=rec.get('type', 'str'),
                updated_at=rec.get('updated_at'),
            ))
        return res

    @staticmethod
    def sender_username(text: str) -> str | None:
        """Peek at the payload's ``from`` field without decrypting.

           Mirrors jseeqret's import handler, which falls back to the
           payload's sender when the operator doesn't name one.
        """
        try:
            return _username_of(json.loads(text).get('from'))
        except (json.JSONDecodeError, AttributeError):
            return None
