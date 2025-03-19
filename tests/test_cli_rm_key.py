from click.testing import CliRunner

from seeqret.db_utils import debug_fetch_users, debug_secrets
from seeqret.main import cli, user, users, init, list, get
from seeqret.cli_group_add import key as add_key
from seeqret.cli_group_rm import key as rm_key
from tests.clirunner_utils import print_result


def test_rm_key():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        result = runner.invoke(init, [
            '.',
            '--user=test',
            '--email=test@example.com', 
        ])
        if result.exit_code != 0: print_result(result)
        assert result.exit_code == 0

        result = runner.invoke(add_key, [
            'FOO', 'BAR',
            '--app=myapp',
            '--env=dev'
        ])
        if result.exit_code != 0: print_result(result)
        assert result.exit_code == 0

        result = runner.invoke(rm_key, ["myapp:dev:FOO"])
        if result.exit_code != 0: print_result(result)
        assert result.exit_code == 0

        result = runner.invoke(list, [
            '-f=myapp:dev:FOO'
        ])
        if result.exit_code != 0: print_result(result)
        assert result.exit_code == 0
        assert "No matching secrets found." in result.output
