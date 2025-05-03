import os

from seeqret.run_utils import current_user, run, seeqret_dir, is_initialized
from click.testing import CliRunner
from seeqret.main import cli, init, validate_current_user
from seeqret.migrations.utils import current_version
from tests.clirunner_utils import print_result


def test_current_user():
    print("CURRENT:USER:", current_user)
    assert current_user()


def test_run():
    assert "hello" in run('echo "hello"', echo=False).strip()
    assert "hello" in run('echo "hello"', echo=True).strip()


def test_seeqret_dir():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        result = runner.invoke(init, [
            '.',
            '--user=' + current_user(),
            '--email=test@example.com',
        ])
        if result.exit_code != 0:  print_result(result)
        assert result.exit_code == 0

        with seeqret_dir():
            assert os.path.exists("seeqrets.db")


def test_is_initialized():
    assert is_initialized() in [True, False]

