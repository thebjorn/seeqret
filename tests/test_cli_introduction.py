import re
import sys

from click.testing import CliRunner
from seeqret.main import cli, init, introduction
from seeqret.migrations.utils import current_version
from tests.clirunner_utils import print_result
from seeqret.run_utils import current_user


def test_introduction():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        result = runner.invoke(init, [
            '.',
            '--user=' + current_user(),
            '--email=test@example.com',
        ])
        if result.exit_code != 0:  print_result(result)
        assert result.exit_code == 0

        result = runner.invoke(introduction)
        if result.exit_code != 0:  print_result(result)
        assert result.exit_code == 0

        assert re.search(r"seeqret add user --username \S+ --email \S+ --pubkey \S+", result.output)
        assert current_user() in result.output
        assert "test@example.com" in result.output
