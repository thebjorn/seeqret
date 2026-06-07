from click.testing import CliRunner

from seeqret.main import init, export
from seeqret.models import User
from seeqret.run_utils import current_user
from seeqret.storage.sqlite_storage import SqliteStorage
from tests.clirunner_utils import print_result


PUBKEY = 'MBiGKmtpckXspJkmijIPXd8GrIAgAdLOoM4pZNOyDzw='


def _init_vault(runner):
    result = runner.invoke(init, [
        '.',
        '--user=' + current_user(),
        '--email=test@example.com',
    ])
    if result.exit_code != 0:
        print_result(result)
    assert result.exit_code == 0


def test_export_to_all_lists_other_users():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        storage = SqliteStorage()
        storage.add_user(User('alice@mac', 'a@example.com', PUBKEY))
        storage.add_user(User('bob@hpc', 'b@example.com', PUBKEY))

        result = runner.invoke(export, ['--to', 'all'])
        if result.exit_code != 0:
            print_result(result)
        assert result.exit_code == 0
        assert 'Seeqrets for alice@mac:' in result.output
        assert 'Seeqrets for bob@hpc:' in result.output
        # the owner is excluded from "all"
        assert f'Seeqrets for {current_user()}:' not in result.output


def test_export_to_all_no_other_users():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)

        result = runner.invoke(export, ['--to', 'all'])
        if result.exit_code != 0:
            print_result(result)
        assert result.exit_code == 0
        assert 'No users to export to.' in result.output
