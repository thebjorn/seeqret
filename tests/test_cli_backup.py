import os

from click.testing import CliRunner

from seeqret.main import cli
from seeqret.run_utils import current_user
from tests.clirunner_utils import print_result


def test_backup_writes_encrypted_html():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        result = runner.invoke(cli, [
            'init', '.',
            '--user=' + current_user(),
            '--email=test@example.com',
        ])
        if result.exit_code != 0:  print_result(result)
        assert result.exit_code == 0

        result = runner.invoke(cli, [
            'backup', '--password', 'pw123', '--out', 'vault.html',
        ])
        if result.exit_code != 0:  print_result(result)
        assert result.exit_code == 0
        assert os.path.exists('vault.html')

        with open('vault.html', encoding='utf-8') as f:
            html = f.read()
        # encrypted, self-decrypting viewer -- no plaintext secrets
        assert 'id="vault"' in html
        assert 'crypto.subtle' in html
