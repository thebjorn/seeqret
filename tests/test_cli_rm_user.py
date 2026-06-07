from click.testing import CliRunner

from seeqret.db_utils import debug_fetch_users
from seeqret.main import init, user as add_user_cmd
from seeqret.cli_group_rm import user as rm_user
from seeqret.run_utils import current_user
from tests.clirunner_utils import print_result


def _init_vault(runner):
    result = runner.invoke(init, [
        '.',
        '--user=' + current_user(),
        '--email=test@example.com',
    ])
    if result.exit_code != 0:
        print_result(result)
    assert result.exit_code == 0


def _add_user(runner):
    result = runner.invoke(add_user_cmd, [
        '--username=tkbe',
        '--email=bjorn@tkbe.org',
        '--pubkey=ilxSnX9+NrwmeIzOFtWrl0lPPkxTEATmC39BILX6rWk=',
    ])
    if result.exit_code != 0:
        print_result(result)
    assert result.exit_code == 0


def test_rm_user():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_user(runner)
        assert len(debug_fetch_users()) == 2

        result = runner.invoke(rm_user, ['tkbe'], input='y\n')
        if result.exit_code != 0:
            print_result(result)
        assert result.exit_code == 0
        assert 'tkbe' in result.output

        assert len(debug_fetch_users()) == 1
        assert 'tkbe' not in debug_fetch_users()


def test_rm_user_yes_flag():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_user(runner)

        result = runner.invoke(rm_user, ['tkbe', '--yes'])
        if result.exit_code != 0:
            print_result(result)
        assert result.exit_code == 0
        assert len(debug_fetch_users()) == 1


def test_rm_user_abort_keeps_user():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_user(runner)

        result = runner.invoke(rm_user, ['tkbe'], input='n\n')
        if result.exit_code != 0:
            print_result(result)
        assert result.exit_code == 0
        assert 'Aborting.' in result.output
        assert len(debug_fetch_users()) == 2


def test_rm_user_unknown():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)

        result = runner.invoke(rm_user, ['nope'], input='y\n')
        assert result.exit_code != 0
        assert 'Unknown user' in result.output


def test_rm_user_cannot_remove_owner():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)

        result = runner.invoke(rm_user, [current_user(), '--yes'])
        assert result.exit_code != 0
        assert 'owner' in result.output.lower()
        assert len(debug_fetch_users()) == 1
