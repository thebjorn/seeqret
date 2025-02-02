import re
import sys

from click.testing import CliRunner
from seeqret.main import users, init
from tests.clirunner_utils import print_result
from seeqret.run_utils import current_user


def test_users():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        result = runner.invoke(init, [
            '.',
            '--user=' + current_user(),
            '--email=test@example.com',
        ])
        if result.exit_code != 0:  print_result(result)
        assert result.exit_code == 0
    
        result = runner.invoke(users)
        if result.exit_code != 0:  print_result(result)
        assert result.exit_code == 0

        result = runner.invoke(users, ['--export'])
        if result.exit_code != 0:  print_result(result)
        assert result.exit_code == 0
