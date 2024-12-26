import re
import sys

from click.testing import CliRunner
from seeqret.main import cli, init
from seeqret.migrations.utils import current_version


def test_init():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        result = runner.invoke(init, [
            '.',
            '--user=test',
            '--email=test@example.com',
        ])
        assert result.exit_code == 0
        if sys.platform == 'win32':
            assert 'vault_dir permissions are ok' in result.output
            assert 'vault is encrypted' in result.output
        assert 'seeqret.key created' in result.output

        import sqlite3
        cn = sqlite3.connect('seeqret/seeqrets.db')
        assert current_version(cn) >= 2


def test_init_no_dir():
    runner = CliRunner(env=dict(TESTING="TRUE"))

    result = runner.invoke(init, [
        '/this/path/does/not/exist',
        '--user=test',
        '--email=test@example.com',
    ])

    assert re.search(r'Error: The parent of the vault: .*? must exist.', result.output)
