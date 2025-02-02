import re
import sys

from click.testing import CliRunner
from seeqret.main import owner, init
from tests.clirunner_utils import print_result


def test_info():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        result = runner.invoke(init, [
            '.',
            # '--user=test',
            '--email=test@example.com',
        ])
        if result.exit_code != 0:  print_result(result)
        assert result.exit_code == 0
    
        result = runner.invoke(owner)
        if result.exit_code != 0:  print_result(result)
        assert result.exit_code == 0
