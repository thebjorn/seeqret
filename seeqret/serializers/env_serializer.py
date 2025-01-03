from .serializer import serializer, BaseSerializer


@serializer
class EnvSerializer(BaseSerializer):
    """Export to .env file.
    """
    version = 1
    tag = 'env'

    def dumps(self, secrets, system):
        if system == 'linux':
            return "don't write .env files on linux"

        res = []
        for secret in secrets:
            res.append(f'{secret.key}={secret.value}')

        return '\n'.join(res)

    def loads(self, secrets, system):
        raise NotImplementedError()
