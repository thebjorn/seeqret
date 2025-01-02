from click.testing import CliRunner

from seeqret import cd
from seeqret.db_utils import debug_fetch_users, debug_secrets
from seeqret.main import cli, user, users, init, list, export, serializers, save
from seeqret.cli_group_add import key
from seeqret.storage.sqlite_storage import SqliteStorage
from tests.clirunner_utils import print_result


def test_command_roundtrip():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        # print("\nINIT:--------------------------------")
        result = runner.invoke(init, [
            '.',
            '--user=test',
            '--email=test@example.com',
        ])
        assert result.exit_code == 0

        # print("\nADD:KEY:-------------------------------")
        result = runner.invoke(key, [
            'FOO', 'BAR',
            '--app=myapp',
            '--env=dev'
        ])
        assert result.exit_code == 0
        assert len(debug_fetch_users()) == 1

        # print("\nSERIALIZERS----------------------------")
        result = runner.invoke(serializers, [])
        assert result.exit_code == 0
        # print_result(result)

        # print("\nLIST:----------------------------------")
        result = runner.invoke(list, [])
        print_result(result)

        # print("\nEXPORT:--------------------------------")
        result = runner.invoke(export, [
            'self',
            '-fFOO',
            '-scommand'
        ])
        assert result.exit_code == 0
        print_result(result)
        output = result.output.split()[2:]

        with cd('seeqret'):
            storage = SqliteStorage()
            storage._remove_secrets(key='FOO')

        result = runner.invoke(save, output)
        assert result.exit_code == 0
        # print_result(result)

        with cd('seeqret'):
            storage = SqliteStorage()
            secrets = storage.fetch_secrets(key='FOO')
            assert len(secrets) == 1
            secret = secrets[0]
            assert secret.key == 'FOO'
            assert secret.value == 'BAR'
