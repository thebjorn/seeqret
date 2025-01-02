from click.testing import CliRunner

from seeqret.db_utils import debug_fetch_users, debug_secrets
from seeqret.main import cli, user, users, init, list
from seeqret.cli_group_add import key
from tests.clirunner_utils import print_result


def test_add_key():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        result = runner.invoke(init, [
            '.',
            '--user=test',
            '--email=test@example.com',
        ])
        if result.exit_code != 0: print_result(result)
        assert result.exit_code == 0

        assert len(debug_secrets()) == 0
        result = runner.invoke(list)
        assert result.exit_code == 0

        result = runner.invoke(key, [
            'FOO', 'BAR',
            '--app=myapp',
            '--env=dev'
        ])
        if result.exit_code != 0: print_result(result)
        assert result.exit_code == 0
        assert len(debug_fetch_users()) == 1
