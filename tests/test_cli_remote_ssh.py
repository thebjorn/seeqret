from unittest.mock import patch, MagicMock

from click.testing import CliRunner

from seeqret.cli_group_add import key
from seeqret.cli_group_push import push as push_group
from seeqret.cli_group_remote import remote as remote_group
from seeqret.cli_group_verify import verify as verify_group
from seeqret.main import init
from seeqret.run_utils import current_user
from tests.clirunner_utils import print_result


SERVER = 'deploy@server.example.com'
SET_CMD = 'source /srv/bin/go dkpw set -k {key} -v {value}'
SET_CMD_STDIN = 'source /srv/bin/go dkpw set -k {key} --stdin'
GET_CMD = 'source /srv/bin/go dkpw get {key} -s'


def _init_vault(runner):
    result = runner.invoke(init, [
        '.',
        '--user=' + current_user(),
        '--email=test@example.com',
    ])
    if result.exit_code != 0:
        print_result(result)
    assert result.exit_code == 0


def _add_secret(runner, name, value, app='myapp', env='prod'):
    result = runner.invoke(key, [name, value, '--app=' + app, '--env=' + env])
    if result.exit_code != 0:
        print_result(result)
    assert result.exit_code == 0


def _add_server(runner, get_cmd=GET_CMD, set_cmd=SET_CMD):
    args = ['add', 'myserver', SERVER, '--set', set_cmd]
    if get_cmd:
        args += ['--get', get_cmd]
    result = runner.invoke(remote_group, args)
    if result.exit_code != 0:
        print_result(result)
    assert result.exit_code == 0
    return result


def test_remote_add_list_rm():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_server(runner)

        result = runner.invoke(remote_group, ['list'])
        assert result.exit_code == 0
        assert 'myserver' in result.output
        assert SERVER in result.output
        assert 'dkpw set' in result.output
        assert 'dkpw get' in result.output

        result = runner.invoke(remote_group, ['rm', 'myserver'])
        assert result.exit_code == 0

        result = runner.invoke(remote_group, ['list'])
        assert result.exit_code == 0
        assert 'No remotes registered' in result.output


def test_remote_add_updates_existing_alias():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_server(runner)

        result = runner.invoke(remote_group, [
            'add', 'myserver', 'other@example.com',
            '--set', 'newtool set {key} {value}',
        ])
        assert result.exit_code == 0

        result = runner.invoke(remote_group, ['list'])
        assert 'other@example.com' in result.output
        assert 'newtool' in result.output
        assert SERVER not in result.output


def test_remote_add_rejects_bad_userhost():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)

        result = runner.invoke(remote_group, [
            'add', 'myserver', 'no-at-sign', '--set', SET_CMD,
        ])
        assert result.exit_code != 0
        assert 'USER@HOST' in result.output


def test_remote_add_requires_placeholders():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)

        result = runner.invoke(remote_group, [
            'add', 'myserver', SERVER, '--set', 'dkpw set -k KEY',
        ])
        assert result.exit_code != 0
        assert '{key}' in result.output


def test_remote_rm_unknown_alias():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)

        result = runner.invoke(remote_group, ['rm', 'nosuch'])
        assert result.exit_code != 0
        assert 'No remote named nosuch' in result.output


def test_push_remote_runs_ssh():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_secret(runner, 'FOO', 'secret123')
        _add_server(runner)

        ok = MagicMock(returncode=0, stdout='', stderr='')

        with patch('subprocess.run', return_value=ok) as mock_run:
            result = runner.invoke(push_group, ['myserver', 'myapp:prod:FOO'])

        if result.exit_code != 0:
            print_result(result)
        assert result.exit_code == 0
        assert 'pushed FOO' in result.output

        calls = mock_run.call_args_list
        assert len(calls) == 1
        assert calls[0].args[0] == [
            'ssh', SERVER,
            'source /srv/bin/go dkpw set -k FOO -v secret123',
        ]


def test_push_remote_quotes_value():
    """Values with shell metacharacters are quoted for the remote."""
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_secret(runner, 'FOO', "it's $HOME here")
        _add_server(runner)

        ok = MagicMock(returncode=0, stdout='', stderr='')

        with patch('subprocess.run', return_value=ok) as mock_run:
            result = runner.invoke(push_group, ['myserver', 'myapp:prod:FOO'])

        assert result.exit_code == 0
        remote_cmd = mock_run.call_args.args[0][2]
        # shlex.quote wraps in single quotes; $HOME must not be bare.
        assert remote_cmd == (
            "source /srv/bin/go dkpw set -k FOO "
            "-v 'it'\"'\"'s $HOME here'"
        )


def test_remote_add_reports_value_mode():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)

        result = _add_server(runner, set_cmd=SET_CMD_STDIN)
        assert 'piped on stdin' in result.output

        result = _add_server(runner, set_cmd=SET_CMD)
        assert 'on the remote command line' in result.output


def test_push_remote_stdin_mode():
    """A set template without {value} pipes the value on stdin."""
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_secret(runner, 'FOO', 'secret123')
        _add_server(runner, set_cmd=SET_CMD_STDIN)

        ok = MagicMock(returncode=0, stdout='', stderr='')

        with patch('subprocess.run', return_value=ok) as mock_run:
            result = runner.invoke(push_group, ['myserver', 'myapp:prod:FOO'])

        if result.exit_code != 0:
            print_result(result)
        assert result.exit_code == 0

        call = mock_run.call_args
        assert call.args[0] == [
            'ssh', SERVER,
            'source /srv/bin/go dkpw set -k FOO --stdin',
        ]
        assert call.kwargs.get('input') == 'secret123'


def test_push_remote_cmdline_mode_no_stdin():
    """A set template with {value} does not pipe anything on stdin."""
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_secret(runner, 'FOO', 'secret123')
        _add_server(runner)

        ok = MagicMock(returncode=0, stdout='', stderr='')

        with patch('subprocess.run', return_value=ok) as mock_run:
            result = runner.invoke(push_group, ['myserver', 'myapp:prod:FOO'])

        assert result.exit_code == 0
        assert mock_run.call_args.kwargs.get('input') is None


def test_push_remote_stdin_mode_dry_run():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_secret(runner, 'FOO', 'secret123')
        _add_server(runner, set_cmd=SET_CMD_STDIN)

        with patch('subprocess.run') as mock_run:
            result = runner.invoke(
                push_group, ['myserver', 'myapp:prod:FOO', '--dry-run'],
            )

        if result.exit_code != 0:
            print_result(result)
        assert result.exit_code == 0
        assert 'dkpw set -k FOO --stdin' in result.output
        assert '(value on stdin)' in result.output
        assert 'secret123' not in result.output
        mock_run.assert_not_called()


def test_push_remote_dry_run_masks_value():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_secret(runner, 'FOO', 'secret123')
        _add_server(runner)

        with patch('subprocess.run') as mock_run:
            result = runner.invoke(
                push_group, ['myserver', 'myapp:prod:FOO', '--dry-run'],
            )

        if result.exit_code != 0:
            print_result(result)
        assert result.exit_code == 0
        assert 'would push FOO' in result.output
        assert f'ssh {SERVER}' in result.output
        assert 'dkpw set -k FOO' in result.output
        assert '*****' in result.output
        assert 'secret123' not in result.output
        mock_run.assert_not_called()


def test_push_remote_failure():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_secret(runner, 'FOO', 'secret123')
        _add_server(runner)

        fail = MagicMock(returncode=255, stdout='', stderr='connection refused')

        with patch('subprocess.run', return_value=fail):
            result = runner.invoke(push_group, ['myserver', 'myapp:prod:FOO'])

        assert result.exit_code != 0
        assert 'FAILED FOO' in result.output
        assert 'connection refused' in result.output


def test_push_unknown_alias_is_unknown_command():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)

        result = runner.invoke(push_group, ['nosuch', 'myapp:prod:FOO'])
        assert result.exit_code != 0
        assert 'No such command' in result.output


def test_push_help_lists_remote_aliases():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_server(runner)

        result = runner.invoke(push_group, ['--help'])
        assert result.exit_code == 0
        assert 'myserver' in result.output
        assert 'vercel' in result.output


def test_verify_remote_ok():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_secret(runner, 'FOO', 'secret123')
        _add_server(runner)

        ok = MagicMock(returncode=0, stdout='secret123\n', stderr='')

        with patch('subprocess.run', return_value=ok) as mock_run:
            result = runner.invoke(
                verify_group, ['myserver', 'myapp:prod:FOO'],
            )

        if result.exit_code != 0:
            print_result(result)
        assert result.exit_code == 0
        assert 'ok' in result.output
        assert 'secret123' not in result.output

        assert mock_run.call_args.args[0] == [
            'ssh', SERVER, 'source /srv/bin/go dkpw get FOO -s',
        ]


def test_verify_remote_mismatch():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_secret(runner, 'FOO', 'secret123')
        _add_server(runner)

        other = MagicMock(returncode=0, stdout='different\n', stderr='')

        with patch('subprocess.run', return_value=other):
            result = runner.invoke(
                verify_group, ['myserver', 'myapp:prod:FOO'],
            )

        assert result.exit_code != 0
        assert 'MISMATCH FOO' in result.output
        assert 'secret123' not in result.output
        assert 'different' not in result.output


def test_verify_remote_missing():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_secret(runner, 'FOO', 'secret123')
        _add_server(runner)

        fail = MagicMock(returncode=1, stdout='', stderr='no such key')

        with patch('subprocess.run', return_value=fail):
            result = runner.invoke(
                verify_group, ['myserver', 'myapp:prod:FOO'],
            )

        assert result.exit_code != 0
        assert 'MISSING' in result.output
        assert 'FOO' in result.output


def test_verify_remote_without_get_cmd():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_secret(runner, 'FOO', 'secret123')
        _add_server(runner, get_cmd=None)

        with patch('subprocess.run') as mock_run:
            result = runner.invoke(
                verify_group, ['myserver', 'myapp:prod:FOO'],
            )

        assert result.exit_code != 0
        assert 'no get command' in result.output
        mock_run.assert_not_called()


def test_push_remote_multiple_secrets():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_secret(runner, 'FOO', 'v1')
        _add_secret(runner, 'BAR', 'v2')
        _add_server(runner)

        ok = MagicMock(returncode=0, stdout='', stderr='')

        with patch('subprocess.run', return_value=ok) as mock_run:
            result = runner.invoke(push_group, ['myserver', 'myapp:prod:*'])

        if result.exit_code != 0:
            print_result(result)
        assert result.exit_code == 0
        assert len(mock_run.call_args_list) == 2
        assert 'Pushed 2 secret(s)' in result.output
