import re
import sys
from click.testing import CliRunner

from seeqret import __version__
from seeqret.db_utils import debug_fetch_users, debug_secrets
from seeqret.main import (
    cli, user, users, init, list, env,
    parse_version, check_version_requirement, parse_env_template_version
)
from seeqret.cli_group_add import key
from tests.clirunner_utils import print_result

from seeqret.migrations.utils import current_version
from seeqret.run_utils import current_user


def test_env():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        result = runner.invoke(init, [
            '.',
            '--user=' + current_user(),
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
        
        with open('env.template', 'w') as f:
            f.write(':dev\n')
        result = runner.invoke(env)
        if result.exit_code != 0: print_result(result)

        assert result.exit_code == 0
        assert 'FOO="BAR"' in open('.env').read()


def test_parse_version():
    assert parse_version('0.2.2') == (0, 2, 2)
    assert parse_version('1.0') == (1, 0)
    assert parse_version('0.3') == (0, 3)
    assert parse_version('10.20.30') == (10, 20, 30)


def test_check_version_requirement():
    assert check_version_requirement('>=0.3', '0.3.0')[0] is True
    assert check_version_requirement('>=0.3', '0.2.2')[0] is False
    assert check_version_requirement('>=0.3', '0.4')[0] is True
    assert check_version_requirement('>0.2.2', '0.2.3')[0] is True
    assert check_version_requirement('>0.2.2', '0.2.2')[0] is False
    assert check_version_requirement('==0.3', '0.3')[0] is True
    assert check_version_requirement('==0.3', '0.3.0')[0] is False
    assert check_version_requirement('<1.0', '0.9')[0] is True
    assert check_version_requirement('<=0.3', '0.3')[0] is True


def test_parse_env_template_version():
    assert parse_env_template_version('@seeqret>=0.3') == '>=0.3'
    assert parse_env_template_version('@seeqret>0.2.2') == '>0.2.2'
    assert parse_env_template_version('@seeqret == 0.3') == '== 0.3'
    assert parse_env_template_version('@SEEQRET>=1.0') == '>=1.0'
    assert parse_env_template_version('# just a comment') is None
    assert parse_env_template_version(':dev:FOO*') is None


def test_env_version_check():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        result = runner.invoke(init, [
            '.',
            '--user=' + current_user(),
            '--email=test@example.com',
        ])
        assert result.exit_code == 0

        result = runner.invoke(key, [
            'FOO', 'BAR',
            '--app=myapp',
            '--env=dev'
        ])
        assert result.exit_code == 0

        # Test with version requirement that should pass
        with open('env.template', 'w') as f:
            f.write(f'@seeqret>={__version__}\n')
            f.write(':dev\n')
        result = runner.invoke(env)
        assert result.exit_code == 0

        # Test with version requirement that should fail
        with open('env.template', 'w') as f:
            f.write('@seeqret>=99.0\n')
            f.write(':dev\n')
        result = runner.invoke(env)
        assert result.exit_code == 1
        assert 'requires seeqret>=99.0' in result.output
        assert 'pip install --upgrade seeqret' in result.output

        # Test with invalid @ directive (misspelled)
        with open('env.template', 'w') as f:
            f.write('@secret>=0.3\n')
            f.write(':dev\n')
        result = runner.invoke(env)
        assert result.exit_code == 1
        assert 'Invalid directive' in result.output
        assert '@secret>=0.3' in result.output
        assert 'Expected format: @seeqret>=VERSION' in result.output
