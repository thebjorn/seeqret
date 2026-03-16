from unittest.mock import patch, MagicMock

from click.testing import CliRunner
from seeqret.cli_group_add import key
from seeqret.main import setenv, init
from tests.clirunner_utils import print_result
from seeqret.run_utils import current_user


def test_setenv_dry_run():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        result = runner.invoke(init, [
            '.',
            '--user=' + current_user(),
            '--email=test@example.com',
        ])
        if result.exit_code != 0: print_result(result)
        assert result.exit_code == 0

        result = runner.invoke(key, [
            'DB_PASS', 'secret123',
            '--app=myapp',
            '--env=prod'
        ])
        if result.exit_code != 0: print_result(result)
        assert result.exit_code == 0

        result = runner.invoke(setenv, ['myapp:prod:DB_PASS', '--dry-run'])
        if result.exit_code != 0: print_result(result)
        assert result.exit_code == 0
        assert 'set "DB_PASS=secret123"' in result.output


def test_setenv_multiple_dry_run():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        result = runner.invoke(init, [
            '.',
            '--user=' + current_user(),
            '--email=test@example.com',
        ])
        assert result.exit_code == 0

        for name, val in [('DB_HOST', 'localhost'), ('DB_PORT', '5432')]:
            result = runner.invoke(key, [
                name, val,
                '--app=myapp',
                '--env=prod'
            ])
            assert result.exit_code == 0

        result = runner.invoke(setenv, ['myapp:prod:*', '--dry-run'])
        if result.exit_code != 0: print_result(result)
        assert result.exit_code == 0
        assert 'set "DB_HOST=localhost"' in result.output
        assert 'set "DB_PORT=5432"' in result.output


def test_setenv_no_secrets():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        result = runner.invoke(init, [
            '.',
            '--user=' + current_user(),
            '--email=test@example.com',
        ])
        assert result.exit_code == 0

        result = runner.invoke(setenv, ['nonexistent:app:KEY'])
        assert result.exit_code != 0
        assert 'No secrets found' in result.output


def test_setenv_duplicate_keys():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        result = runner.invoke(init, [
            '.',
            '--user=' + current_user(),
            '--email=test@example.com',
        ])
        assert result.exit_code == 0

        # Add same key name in two different app/env combos
        result = runner.invoke(key, [
            'API_KEY', 'val1',
            '--app=app1',
            '--env=dev'
        ])
        assert result.exit_code == 0

        result = runner.invoke(key, [
            'API_KEY', 'val2',
            '--app=app2',
            '--env=dev'
        ])
        assert result.exit_code == 0

        result = runner.invoke(setenv, ['::API_KEY', '--dry-run'])
        assert result.exit_code != 0
        assert 'Duplicate key' in result.output


def test_setenv_calls_setx():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        result = runner.invoke(init, [
            '.',
            '--user=' + current_user(),
            '--email=test@example.com',
        ])
        assert result.exit_code == 0

        result = runner.invoke(key, [
            'MY_VAR', 'myvalue',
            '--app=myapp',
            '--env=prod'
        ])
        assert result.exit_code == 0

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = 'SUCCESS'

        with patch('subprocess.run', return_value=mock_result) as mock_run:
            result = runner.invoke(setenv, ['myapp:prod:MY_VAR'])
            if result.exit_code != 0: print_result(result)
            assert result.exit_code == 0
            mock_run.assert_called_once_with(
                ['setx', 'MY_VAR', 'myvalue'],
                capture_output=True, text=True
            )
            assert 'MY_VAR set' in result.output
            assert '1 environment variable' in result.output
            assert 'new terminal' in result.output
            assert 'set "MY_VAR=myvalue"' in result.output
