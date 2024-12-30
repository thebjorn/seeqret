from .serializer import BaseSerializer, serializer, ValidationError
from ..models import Secret


# from ..seeqrypt.nacl_backend import hash_message


@serializer
class CommandSerializer(BaseSerializer):
    """Help text jsoncrypt.
    """
    version = 1
    tag = 'command'

    def dumps(self, secrets, system):
        res = []
        quote = '"' if system == 'win32' else "'"
        for s in secrets:
            val = s.encrypt_to_string(self.sender_private_key,
                                      self.receiver_public_key)
            res.append(
                f'seeqret save -u {self.sender.username} -s command '
                f'-v {quote}{self.version}::{val}{quote}'
            )
        return '\n'.join(res)

    def _validate(self, txt):
        if not isinstance(txt, str):
            raise ValidationError('Text must be a string')
        params = txt.split(':', 7)
        if len(params) != 8:
            raise ValidationError('Text must contain 8 parameters')
        version, _, fingerprint, app, env, key, type, val = params
        print("PARAMS:", params)
        if int(version) != self.version:
            raise ValidationError(
                f"Version mismatch, found {version} - expected {self.version}"
            )

        secret = Secret(
            app=app,
            env=env,
            key=key,
            value=Secret.decrypt_value(  # FIXME: fails here
                val, self.sender_public_key, self.receiver_private_key
            ),
            type=type,
        )
        # if fingerprint != secret.fingerprint():
        #     raise ValidationError("invalid fingerprint")

        return secret

    def load(self, text):
        return [self._validate(text)]
