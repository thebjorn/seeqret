import re
import sys

from click.testing import CliRunner
from seeqret.main import cli, init, validate_current_user
from seeqret.migrations.utils import current_version
from tests.clirunner_utils import print_result
from seeqret.run_utils import current_user


def test_init():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        result = runner.invoke(init, [
            '.',
            '--user=' + current_user(),
            '--email=test@example.com',
        ])
        if result.exit_code != 0:  print_result(result)
        assert result.exit_code == 0
        if sys.platform == 'win32':
            assert 'vault_dir permissions are ok' in result.output
            assert 'vault is encrypted' in result.output
        assert 'seeqret.key created' in result.output

        import sqlite3
        cn = sqlite3.connect('seeqret/seeqrets.db')
        assert current_version(cn) >= 2

        assert validate_current_user()


def test_init_no_dir():
    runner = CliRunner(env=dict(TESTING="TRUE"))

    result = runner.invoke(init, [
        '/this/path/does/not/exist',
        '--user=test',
        '--email=test@example.com',
    ])

    assert re.search(r'Error: The parent of the vault: .*? must exist.', result.output)
