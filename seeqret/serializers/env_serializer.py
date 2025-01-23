from .serializer import serializer, BaseSerializer
from ..models import Secret


@serializer
class EnvSerializer(BaseSerializer):
    """Export to .env file.
    """
    version = 1
    tag = 'env'

    def dumps(self, secrets, system) -> str:
        if system == 'linux':
            return "don't write .env files on linux"

        res = []
        for secret in secrets:
            res.append(f'{secret.key}="{secret.value}"')

        return '\n'.join(res)

    def load(self, text: str, **kw) -> list[Secret]:
        lines = text.split('\n')
        return [Secret(
            key=line.split('=', 1)[0],
            plaintext_value=line.split('=', 1)[1].strip('"'),
            app=kw.get('app', '*'),
            env=kw.get('env', '*'),
            type=kw.get('type', 'str')
        ) for line in lines]
