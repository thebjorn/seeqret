from click.testing import CliRunner
from seeqret.main import cli, init


def test_init():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        result = runner.invoke(init, [
            '.',
            '--user=test',
            '--email=test@example.com',
        ])
        assert result.exit_code == 0
        assert 'vault_dir permissions are ok' in result.output
        assert 'vault is encrypted' in result.output
        assert 'seeqret.key created' in result.output


def test_init_no_dir():
    runner = CliRunner(env=dict(TESTING="TRUE"))

    result = runner.invoke(init, [
        'c:/this/path/does/not/exist',
        '--user=test',
        '--email=test@example.com',
    ])
    assert r'Error: The parent of the vault: C:\this\path\does\not\exist must exist.' in result.output
