from click.testing import CliRunner

from seeqret.main import cli, init, importenv, list, parse_env_line
from seeqret.run_utils import current_user
from tests.clirunner_utils import print_result


def test_parse_env_line():
    # Basic formats
    assert parse_env_line('KEY=value') == ('KEY', 'value')
    assert parse_env_line('KEY="value"') == ('KEY', 'value')
    assert parse_env_line("KEY='value'") == ('KEY', 'value')
    
    # With spaces
    assert parse_env_line('  KEY = value  ') == ('KEY', 'value')
    assert parse_env_line('KEY="value with spaces"') == ('KEY', 'value with spaces')
    
    # Export format
    assert parse_env_line('export KEY=value') == ('KEY', 'value')
    assert parse_env_line('export KEY="value"') == ('KEY', 'value')
    
    # Comments and empty lines
    assert parse_env_line('') is None
    assert parse_env_line('# comment') is None
    assert parse_env_line('  # comment') is None
    
    # Edge cases
    assert parse_env_line('KEY=') == ('KEY', '')
    assert parse_env_line('KEY=value=with=equals') == ('KEY', 'value=with=equals')


def test_importenv():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        # Initialize vault
        result = runner.invoke(init, [
            '.',
            '--user=' + current_user(),
            '--email=test@example.com',
        ])
        assert result.exit_code == 0

        # Create a .env file to import
        with open('test.env', 'w') as f:
            f.write('# This is a comment\n')
            f.write('DATABASE_URL="postgres://localhost/db"\n')
            f.write('API_KEY=secret123\n')
            f.write("SECRET_TOKEN='token456'\n")
            f.write('export EXPORT_VAR=exported\n')

        # Test dry run
        result = runner.invoke(importenv, ['test.env', '--app=myapp', '--env=dev', '--dry-run'])
        if result.exit_code != 0: print_result(result)
        assert result.exit_code == 0
        assert 'Dry run' in result.output
        assert 'DATABASE_URL' in result.output

        # Test actual import
        result = runner.invoke(importenv, ['test.env', '--app=myapp', '--env=dev'])
        if result.exit_code != 0: print_result(result)
        assert result.exit_code == 0
        assert '4 added' in result.output

        # Verify secrets were added
        result = runner.invoke(list, ['-f', 'myapp:dev:'])
        assert result.exit_code == 0
        assert 'DATABASE_URL' in result.output
        assert 'API_KEY' in result.output
        assert 'SECRET_TOKEN' in result.output
        assert 'EXPORT_VAR' in result.output


def test_importenv_skip_existing():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        result = runner.invoke(init, [
            '.',
            '--user=' + current_user(),
            '--email=test@example.com',
        ])
        assert result.exit_code == 0

        # Create and import first file
        with open('first.env', 'w') as f:
            f.write('KEY1=value1\n')
        result = runner.invoke(importenv, ['first.env', '--app=myapp', '--env=dev'])
        assert result.exit_code == 0
        assert '1 added' in result.output

        # Try to import again - should skip
        result = runner.invoke(importenv, ['first.env', '--app=myapp', '--env=dev'])
        assert result.exit_code == 0
        assert '1 skipped' in result.output


def test_importenv_update_existing():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        result = runner.invoke(init, [
            '.',
            '--user=' + current_user(),
            '--email=test@example.com',
        ])
        assert result.exit_code == 0

        # Create and import first file
        with open('first.env', 'w') as f:
            f.write('KEY1=value1\n')
        result = runner.invoke(importenv, ['first.env', '--app=myapp', '--env=dev'])
        assert result.exit_code == 0

        # Update the file and import with --update
        with open('first.env', 'w') as f:
            f.write('KEY1=updated_value\n')
        result = runner.invoke(importenv, ['first.env', '--app=myapp', '--env=dev', '--update'])
        assert result.exit_code == 0
        assert '1 updated' in result.output
