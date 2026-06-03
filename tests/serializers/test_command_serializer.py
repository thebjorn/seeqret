from click.testing import CliRunner

from seeqret.run_utils import cd
from seeqret.db_utils import debug_fetch_users, debug_secrets
from seeqret.main import cli, user, users, init, list, export, serializers, load
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
            '--to=self',
            '-fFOO',
            '-scommand'
        ])
        # assert result.exit_code == 0
        print_result(result)
        # print(result.output)
        output = result.output.split()[5:]

        with cd('seeqret'):
            storage = SqliteStorage()
            storage.remove_secrets(key='FOO')

        result = runner.invoke(load, output)
        if result.exit_code != 0: print_result(result)
        assert result.exit_code == 0
        # print_result(result)

        with cd('seeqret'):
            storage = SqliteStorage()
            secrets = storage.fetch_secrets(key='FOO')
            assert len(secrets) == 1
            secret = secrets[0]
            assert secret.key == 'FOO'
            assert secret.value == 'BAR'


def test_roundtrip_bare_name_resolves_qualified_user():
    """export --to/load -u with a bare name resolve a user@host user (issue #25)."""
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        result = runner.invoke(init, [
            '.',
            '--user=test@somehost',
            '--email=test@example.com',
        ])
        assert result.exit_code == 0

        result = runner.invoke(key, [
            'FOO', 'BAR',
            '--app=myapp',
            '--env=dev',
        ])
        assert result.exit_code == 0

        # bare name resolves to the only matching qualified user
        result = runner.invoke(export, ['--to=test', '-fFOO', '-scommand'])
        if result.exit_code != 0: print_result(result)
        assert result.exit_code == 0
        assert 'Seeqrets for test@somehost:' in result.output
        output = result.output.split()[5:]

        # the emitted command carries the qualified sender name
        assert output[0] == '-utest@somehost'

        with cd('seeqret'):
            storage = SqliteStorage()
            storage.remove_secrets(key='FOO')

        # load with the qualified name from the emitted command
        result = runner.invoke(load, output)
        if result.exit_code != 0: print_result(result)
        assert result.exit_code == 0

        # load again with a bare sender name - resolves the same user
        result = runner.invoke(load, ['-utest'] + output[1:])
        if result.exit_code != 0: print_result(result)
        assert result.exit_code == 0

        with cd('seeqret'):
            storage = SqliteStorage()
            secrets = storage.fetch_secrets(key='FOO')
            assert len(secrets) == 1
            assert secrets[0].value == 'BAR'


def test_load_overwrites_existing_secret():
    """`seeqret load` must overwrite an existing secret with the imported value."""
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        result = runner.invoke(init, [
            '.',
            '--user=test',
            '--email=test@example.com',
        ])
        assert result.exit_code == 0

        # Add a secret, export it, then change the local value.
        result = runner.invoke(key, [
            'FOO', 'BAR',
            '--app=myapp',
            '--env=dev',
        ])
        assert result.exit_code == 0

        result = runner.invoke(export, ['--to=self', '-fFOO', '-scommand'])
        assert result.exit_code == 0
        output = result.output.split()[5:]

        # Locally overwrite to a different value; the import should put it back.
        result = runner.invoke(key, [
            'FOO', 'LOCAL_CHANGE',
            '--app=myapp',
            '--env=dev',
            '--force',
        ])
        assert result.exit_code == 0

        result = runner.invoke(load, output)
        if result.exit_code != 0: print_result(result)
        assert result.exit_code == 0

        with cd('seeqret'):
            storage = SqliteStorage()
            secrets = storage.fetch_secrets(key='FOO')
            assert len(secrets) == 1
            assert secrets[0].value == 'BAR'
