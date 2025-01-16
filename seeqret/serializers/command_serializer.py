from .serializer import BaseSerializer, serializer, ValidationError
from ..models import Secret


@serializer
class CommandSerializer(BaseSerializer):
    """Output list of commands that can be pasted into terminal.
    """
    version = 1
    tag = 'command'

    def dumps(self, secrets, system) -> str:
        res = []
        # quote = '"' if system == 'win32' else "'"
        for s in secrets:
            val = s.encrypt_to_string(self.sender_private_key,
                                      self.receiver_public_key)
            res.append(
                f'seeqret load -u{self.sender.username} -scommand '
                f'-v{self.version}::{val}'
                # f'-v{quote}{self.version}::{val}{quote}'
            )
        return '\n'.join(res)

    def _validate(self, txt: str) -> Secret:
        if not isinstance(txt, str):
            raise ValidationError('Text must be a string')
        params = txt.split(':', 7)
        if len(params) != 8:
            raise ValidationError('Text must contain 8 parameters')
        version, _, fingerprint, app, env, key, type, val = params
        # print("PARAMS:", params)
        if int(version) != self.version:
            raise ValidationError(
                f"Version mismatch, found {version} - expected {self.version}"
            )

        secret = Secret(
            app=app,
            env=env,
            key=key,
            plaintext_value=Secret.decrypt_value(  # FIXME: fails here
                val, self.sender_public_key, self.receiver_private_key
            ).decode('utf-8'),
            type=type,
        )
        if fingerprint != secret.fingerprint():
            raise ValidationError("invalid fingerprint")
        return secret

    def load(self, text: str) -> list[Secret]:
        return [self._validate(text)]
