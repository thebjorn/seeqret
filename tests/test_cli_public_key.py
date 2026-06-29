from click.testing import CliRunner
from seeqret.main import public_key, init
from tests.clirunner_utils import print_result
from seeqret.run_utils import current_user


def test_public_key():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        result = runner.invoke(init, [
            '.',
            '--user=' + current_user(),
            '--email=test@example.com',
        ])
        if result.exit_code != 0:  print_result(result)
        assert result.exit_code == 0

        result = runner.invoke(public_key)
        if result.exit_code != 0:  print_result(result)
        assert result.exit_code == 0
        # only the public key is shown; the private key never is
        assert 'private' not in result.output.lower()
