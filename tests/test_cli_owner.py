import re
import sys

from click.testing import CliRunner
from seeqret.main import owner, init
from tests.clirunner_utils import print_result
from seeqret.run_utils import current_user


def test_owner():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        result = runner.invoke(init, [
            '.',
            '--user=' + current_user(),
            '--email=test@example.com',
        ])
        if result.exit_code != 0:  print_result(result)
        assert result.exit_code == 0
    
        result = runner.invoke(owner)
        if result.exit_code != 0:  print_result(result)
        assert result.exit_code == 0
