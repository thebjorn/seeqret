import os
from unittest.mock import patch, MagicMock

from click.testing import CliRunner

from seeqret.cli_group_add import key
from seeqret.cli_group_verify import vercel as verify_vercel
from seeqret.main import init
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


def _add_secret(runner, name, value, app='myapp', env='prod'):
    result = runner.invoke(key, [name, value, '--app=' + app, '--env=' + env])
    if result.exit_code != 0:
        print_result(result)
    assert result.exit_code == 0


def _link_vercel():
    """Pretend the current dir is a linked Vercel project."""
    os.makedirs('.vercel', exist_ok=True)
    with open(os.path.join('.vercel', 'project.json'), 'w') as f:
        f.write('{"projectId": "test", "orgId": "test"}\n')


def _fake_pull(content, pulled_paths=None):
    """A subprocess.run stand-in that writes ``content`` to the temp
       file ``vercel env pull`` was asked to create.
    """
    def run(args, **kwargs):
        path = args[-1]
        if pulled_paths is not None:
            pulled_paths.append(path)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return MagicMock(returncode=0, stdout='', stderr='')
    return run


def test_verify_vercel_ok():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_secret(runner, 'DB_PASS', 'secret123')
        _link_vercel()

        pull = _fake_pull('# Created by Vercel CLI\nDB_PASS="secret123"\n')

        with patch('shutil.which', return_value='/usr/bin/vercel'), \
             patch('subprocess.run', side_effect=pull):
            result = runner.invoke(
                verify_vercel,
                ['myapp:prod:DB_PASS', '--target=production'],
            )

        if result.exit_code != 0:
            print_result(result)
        assert result.exit_code == 0
        assert 'ok' in result.output
        assert 'DB_PASS' in result.output
        assert 'secret123' not in result.output


def test_verify_vercel_mismatch():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_secret(runner, 'DB_PASS', 'secret123')
        _link_vercel()

        pull = _fake_pull('DB_PASS="different"\n')

        with patch('shutil.which', return_value='/usr/bin/vercel'), \
             patch('subprocess.run', side_effect=pull):
            result = runner.invoke(
                verify_vercel,
                ['myapp:prod:DB_PASS', '--target=production'],
            )

        assert result.exit_code != 0
        assert 'MISMATCH DB_PASS' in result.output
        # Neither the vault value nor the pulled value may leak.
        assert 'secret123' not in result.output
        assert 'different' not in result.output


def test_verify_vercel_sensitive_unverifiable():
    """Sensitive vars pull as empty strings; that is not a MISMATCH.

       Vercel never returns the value of sensitive variables, so an
       empty pulled value against a non-empty vault value is reported
       as SENSITIVE (unverifiable) and does not fail the verify.
    """
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_secret(runner, 'DB_PASS', 'secret123')
        _link_vercel()

        pull = _fake_pull('DB_PASS=""\n')

        with patch('shutil.which', return_value='/usr/bin/vercel'), \
             patch('subprocess.run', side_effect=pull):
            result = runner.invoke(
                verify_vercel,
                ['myapp:prod:DB_PASS', '--target=production'],
            )

        if result.exit_code != 0:
            print_result(result)
        assert result.exit_code == 0
        assert 'SENSITIVE DB_PASS (unverifiable)' in result.output
        assert 'MISMATCH' not in result.output
        assert '1 sensitive secret(s) could not be verified' in result.output
        assert 'secret123' not in result.output


def test_verify_vercel_sensitive_does_not_mask_failures():
    """A real MISMATCH still fails even when sensitive vars are present."""
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_secret(runner, 'DB_PASS', 'secret123')
        _add_secret(runner, 'API_KEY', 'apikey456')
        _link_vercel()

        pull = _fake_pull('DB_PASS=""\nAPI_KEY="different"\n')

        with patch('shutil.which', return_value='/usr/bin/vercel'), \
             patch('subprocess.run', side_effect=pull):
            result = runner.invoke(
                verify_vercel,
                ['myapp:prod:*', '--target=production'],
            )

        assert result.exit_code != 0
        assert 'SENSITIVE DB_PASS (unverifiable)' in result.output
        assert 'MISMATCH API_KEY' in result.output


def test_verify_vercel_empty_vault_value_is_ok():
    """An empty vault value matching an empty pull is ok, not SENSITIVE."""
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_secret(runner, 'EMPTY_FLAG', '')
        _link_vercel()

        pull = _fake_pull('EMPTY_FLAG=""\n')

        with patch('shutil.which', return_value='/usr/bin/vercel'), \
             patch('subprocess.run', side_effect=pull):
            result = runner.invoke(
                verify_vercel,
                ['myapp:prod:EMPTY_FLAG', '--target=production'],
            )

        if result.exit_code != 0:
            print_result(result)
        assert result.exit_code == 0
        assert 'ok' in result.output
        assert 'SENSITIVE' not in result.output


def test_verify_vercel_missing():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_secret(runner, 'DB_PASS', 'secret123')
        _link_vercel()

        pull = _fake_pull('OTHER="value"\n')

        with patch('shutil.which', return_value='/usr/bin/vercel'), \
             patch('subprocess.run', side_effect=pull):
            result = runner.invoke(
                verify_vercel,
                ['myapp:prod:DB_PASS', '--target=production'],
            )

        assert result.exit_code != 0
        assert 'MISSING' in result.output
        assert 'DB_PASS' in result.output


def test_verify_vercel_removes_temp_file():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_secret(runner, 'DB_PASS', 'secret123')
        _link_vercel()

        pulled_paths = []
        pull = _fake_pull('DB_PASS="secret123"\n', pulled_paths)

        with patch('shutil.which', return_value='/usr/bin/vercel'), \
             patch('subprocess.run', side_effect=pull):
            result = runner.invoke(
                verify_vercel,
                ['myapp:prod:DB_PASS', '--target=production'],
            )

        assert result.exit_code == 0
        assert len(pulled_paths) == 1
        assert not os.path.exists(pulled_paths[0])


def test_verify_vercel_pull_commandline():
    """verify runs `vercel env pull --environment <target> --yes <tmp>`."""
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_secret(runner, 'DB_PASS', 'secret123')
        _link_vercel()

        calls = []

        def pull(args, **kwargs):
            calls.append(args)
            with open(args[-1], 'w', encoding='utf-8') as f:
                f.write('DB_PASS="secret123"\n')
            return MagicMock(returncode=0, stdout='', stderr='')

        with patch('shutil.which', return_value='/usr/bin/vercel'), \
             patch('subprocess.run', side_effect=pull):
            result = runner.invoke(
                verify_vercel,
                ['myapp:prod:DB_PASS', '--target=production'],
            )

        assert result.exit_code == 0
        assert len(calls) == 1
        args = calls[0]
        assert args[:3] == ['/usr/bin/vercel', 'env', 'pull']
        assert '--environment' in args
        assert args[args.index('--environment') + 1] == 'production'
        assert '--yes' in args


def test_verify_vercel_target_aliases():
    """prod and dev expand to production and development."""
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_secret(runner, 'DB_PASS', 'secret123')
        _link_vercel()

        calls = []

        def pull(args, **kwargs):
            calls.append(args)
            with open(args[-1], 'w', encoding='utf-8') as f:
                f.write('DB_PASS="secret123"\n')
            return MagicMock(returncode=0, stdout='', stderr='')

        with patch('shutil.which', return_value='/usr/bin/vercel'), \
             patch('subprocess.run', side_effect=pull):
            result = runner.invoke(
                verify_vercel, ['myapp:prod:DB_PASS', '--target=prod'],
            )
            assert result.exit_code == 0
            result = runner.invoke(
                verify_vercel, ['myapp:prod:DB_PASS', '--target=dev'],
            )
            assert result.exit_code == 0

        envs = [args[args.index('--environment') + 1] for args in calls]
        assert envs == ['production', 'development']


def test_verify_vercel_default_target_is_development():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_secret(runner, 'DB_PASS', 'secret123')
        _link_vercel()

        calls = []

        def pull(args, **kwargs):
            calls.append(args)
            with open(args[-1], 'w', encoding='utf-8') as f:
                f.write('DB_PASS="secret123"\n')
            return MagicMock(returncode=0, stdout='', stderr='')

        with patch('shutil.which', return_value='/usr/bin/vercel'), \
             patch('subprocess.run', side_effect=pull):
            result = runner.invoke(verify_vercel, ['myapp:prod:DB_PASS'])

        assert result.exit_code == 0
        args = calls[0]
        assert args[args.index('--environment') + 1] == 'development'


def test_verify_vercel_unknown_target():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)

        result = runner.invoke(
            verify_vercel, ['myapp:prod:DB_PASS', '--target=staging'],
        )
        assert result.exit_code != 0
        assert 'Unknown Vercel target' in result.output


def test_verify_vercel_escaped_values():
    """Quoted, backslash-escaped values from the env file compare equal."""
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_secret(runner, 'CERT', 'line1\nline2"quoted"')
        _link_vercel()

        pull = _fake_pull('CERT="line1\\nline2\\"quoted\\""\n')

        with patch('shutil.which', return_value='/usr/bin/vercel'), \
             patch('subprocess.run', side_effect=pull):
            result = runner.invoke(
                verify_vercel,
                ['myapp:prod:CERT', '--target=production'],
            )

        if result.exit_code != 0:
            print_result(result)
        assert result.exit_code == 0


def test_verify_vercel_pull_failure():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_secret(runner, 'DB_PASS', 'secret123')
        _link_vercel()

        fail = MagicMock(returncode=1, stdout='', stderr='not authorized')

        with patch('shutil.which', return_value='/usr/bin/vercel'), \
             patch('subprocess.run', return_value=fail):
            result = runner.invoke(
                verify_vercel,
                ['myapp:prod:DB_PASS', '--target=production'],
            )

        assert result.exit_code != 0
        assert 'vercel env pull failed' in result.output
        assert 'not authorized' in result.output


def test_verify_vercel_requires_linked_project():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_secret(runner, 'DB_PASS', 'secret123')

        with patch('shutil.which', return_value='/usr/bin/vercel'):
            result = runner.invoke(
                verify_vercel,
                ['myapp:prod:DB_PASS', '--target=production'],
            )

        assert result.exit_code != 0
        assert 'No linked Vercel project' in result.output


def test_verify_vercel_requires_cli_installed():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_secret(runner, 'DB_PASS', 'secret123')
        _link_vercel()

        with patch('shutil.which', return_value=None):
            result = runner.invoke(
                verify_vercel,
                ['myapp:prod:DB_PASS', '--target=production'],
            )

        assert result.exit_code != 0
        assert 'vercel` CLI was not found' in result.output


def test_verify_vercel_no_match():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _link_vercel()

        with patch('shutil.which', return_value='/usr/bin/vercel'):
            result = runner.invoke(
                verify_vercel,
                ['nonexistent:app:KEY', '--target=production'],
            )

        assert result.exit_code != 0
        assert 'No secrets found' in result.output
