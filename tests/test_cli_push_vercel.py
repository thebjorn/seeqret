import json
import os
from unittest.mock import patch, MagicMock

from click.testing import CliRunner

from seeqret.cli_group_add import key
from seeqret.cli_group_push import vercel as push_vercel
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


def _link_vercel_repo(directories):
    """Pretend the current dir is a monorepo root linked via repo.json."""
    os.makedirs('.vercel', exist_ok=True)
    projects = [
        {'id': f'prj_{i}', 'name': d.split("/")[-1], 'directory': d}
        for i, d in enumerate(directories)
    ]
    with open(os.path.join('.vercel', 'repo.json'), 'w') as f:
        json.dump({'remoteName': 'origin', 'projects': projects}, f)


def test_push_vercel_dry_run_skips_link_check():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_secret(runner, 'DB_PASS', 'secret123')

        result = runner.invoke(
            push_vercel,
            ['myapp:prod:DB_PASS', '--dry-run', '--target=production'],
        )
        if result.exit_code != 0:
            print_result(result)
        assert result.exit_code == 0
        assert 'would push DB_PASS' in result.output
        assert 'production' in result.output


def test_push_vercel_no_match():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)

        result = runner.invoke(
            push_vercel,
            ['nonexistent:app:KEY', '--dry-run', '--target=production'],
        )
        assert result.exit_code != 0
        assert 'No secrets found' in result.output


def test_push_vercel_duplicate_keys():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_secret(runner, 'API_KEY', 'val1', app='app1', env='dev')
        _add_secret(runner, 'API_KEY', 'val2', app='app2', env='dev')

        result = runner.invoke(
            push_vercel, ['::API_KEY', '--dry-run', '--target=production'],
        )
        assert result.exit_code != 0
        assert 'Duplicate key' in result.output


def test_push_vercel_target_is_required():
    """Omitting --target must fail instead of pushing to all envs."""
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_secret(runner, 'DB_PASS', 'secret123')
        _link_vercel()

        with patch('shutil.which', return_value='/usr/bin/vercel'), \
             patch('subprocess.run') as mock_run:
            result = runner.invoke(push_vercel, ['myapp:prod:DB_PASS'])

        assert result.exit_code != 0
        assert '--target' in result.output
        mock_run.assert_not_called()


def test_push_vercel_unknown_target():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_secret(runner, 'DB_PASS', 'secret123')

        result = runner.invoke(
            push_vercel,
            ['myapp:prod:DB_PASS', '--dry-run', '--target=staging'],
        )
        assert result.exit_code != 0
        assert 'Unknown Vercel target' in result.output


def test_push_vercel_requires_linked_project():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_secret(runner, 'DB_PASS', 'secret123')

        with patch('shutil.which', return_value='/usr/bin/vercel'):
            result = runner.invoke(
                push_vercel, ['myapp:prod:DB_PASS', '--target=production'],
            )

        assert result.exit_code != 0
        assert 'No linked Vercel project' in result.output


def test_push_vercel_repo_json_link():
    """A monorepo .vercel/repo.json in an ancestor dir counts as linked."""
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_secret(runner, 'DB_PASS', 'secret123')
        _link_vercel_repo(['apps/myapp', 'apps/other'])
        appdir = os.path.join(os.getcwd(), 'apps', 'myapp')
        os.makedirs(appdir)

        ok = MagicMock(returncode=0, stdout='', stderr='')

        with patch('shutil.which', return_value='/usr/bin/vercel'), \
             patch('subprocess.run', return_value=ok):
            result = runner.invoke(
                push_vercel,
                ['myapp:prod:DB_PASS', '--target=production'],
                obj={'curdir': appdir},
            )

        if result.exit_code != 0:
            print_result(result)
        assert result.exit_code == 0
        assert 'pushed DB_PASS' in result.output


def test_push_vercel_repo_json_unlisted_dir():
    """repo.json that doesn't list the current dir is not a link."""
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_secret(runner, 'DB_PASS', 'secret123')
        _link_vercel_repo(['apps/other'])
        appdir = os.path.join(os.getcwd(), 'apps', 'myapp')
        os.makedirs(appdir)

        with patch('shutil.which', return_value='/usr/bin/vercel'):
            result = runner.invoke(
                push_vercel,
                ['myapp:prod:DB_PASS', '--target=production'],
                obj={'curdir': appdir},
            )

        assert result.exit_code != 0
        assert 'No linked Vercel project' in result.output


def test_push_vercel_requires_cli_installed():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_secret(runner, 'DB_PASS', 'secret123')
        _link_vercel()

        with patch('shutil.which', return_value=None):
            result = runner.invoke(
                push_vercel, ['myapp:prod:DB_PASS', '--target=production'],
            )

        assert result.exit_code != 0
        assert 'vercel` CLI was not found' in result.output


def test_push_vercel_calls_vercel():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_secret(runner, 'DB_PASS', 'secret123')
        _link_vercel()

        ok = MagicMock(returncode=0, stdout='', stderr='')

        with patch('shutil.which', return_value='/usr/bin/vercel'), \
             patch('subprocess.run', return_value=ok) as mock_run:
            result = runner.invoke(
                push_vercel,
                ['myapp:prod:DB_PASS', '--target=production'],
            )

        if result.exit_code != 0:
            print_result(result)
        assert result.exit_code == 0
        assert 'pushed DB_PASS' in result.output

        calls = mock_run.call_args_list
        assert len(calls) == 2

        rm_args = calls[0].args[0]
        assert rm_args[:3] == ['/usr/bin/vercel', 'env', 'rm']
        assert 'DB_PASS' in rm_args
        assert 'production' in rm_args
        assert '--yes' in rm_args

        add_args = calls[1].args[0]
        assert add_args[:3] == ['/usr/bin/vercel', 'env', 'add']
        assert 'DB_PASS' in add_args
        assert 'production' in add_args
        assert calls[1].kwargs.get('input') == 'secret123'


def test_push_vercel_loops_per_target():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_secret(runner, 'DB_PASS', 'secret123')
        _link_vercel()

        ok = MagicMock(returncode=0, stdout='', stderr='')

        with patch('shutil.which', return_value='/usr/bin/vercel'), \
             patch('subprocess.run', return_value=ok) as mock_run:
            result = runner.invoke(
                push_vercel,
                ['myapp:prod:DB_PASS',
                 '--target=production,preview,development'],
            )

        if result.exit_code != 0:
            print_result(result)
        assert result.exit_code == 0

        # 3 targets * (rm + add) = 6 subprocess calls
        calls = mock_run.call_args_list
        assert len(calls) == 6
        # Each call carries exactly one environment, never multiple.
        for call in calls:
            args = call.args[0]
            env_pos = args.index('DB_PASS') + 1
            assert args[env_pos] in ('production', 'preview', 'development')
            # No extra env after the first one.
            tail = args[env_pos + 1:]
            for forbidden in ('production', 'preview', 'development'):
                if args[env_pos] != forbidden:
                    assert forbidden not in tail


def test_push_vercel_filter_option():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_secret(runner, 'DB_PASS', 'secret123')
        _add_secret(runner, 'OTHER', 'noise')

        result = runner.invoke(
            push_vercel,
            ['--filter', 'myapp:prod:DB_PASS', '--dry-run',
             '--target=production'],
        )
        if result.exit_code != 0:
            print_result(result)
        assert result.exit_code == 0
        assert 'would push DB_PASS' in result.output
        assert 'OTHER' not in result.output


def test_push_vercel_failure_reports_error():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        _add_secret(runner, 'DB_PASS', 'secret123')
        _link_vercel()

        rm_ok = MagicMock(returncode=0, stdout='', stderr='')
        add_fail = MagicMock(returncode=1, stdout='', stderr='boom')

        with patch('shutil.which', return_value='/usr/bin/vercel'), \
             patch('subprocess.run', side_effect=[rm_ok, add_fail]):
            result = runner.invoke(
                push_vercel,
                ['myapp:prod:DB_PASS', '--target=production'],
            )

        assert result.exit_code != 0
        assert 'FAILED DB_PASS' in result.output
        assert 'boom' in result.output
