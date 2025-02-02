import re
import sys

from click.testing import CliRunner
from seeqret.cli_group_add import key
from seeqret.main import value, init, get
from tests.clirunner_utils import print_result
from seeqret.run_utils import current_user

def test_edit_value():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        result = runner.invoke(init, [
            '.',
            '--user=' + current_user(),
            '--email=test@example.com',
        ])
        if result.exit_code != 0:  print_result(result)
        assert result.exit_code == 0

        result = runner.invoke(key, [
            'FOO', 'BAR',
            '--app=myapp',
            '--env=dev'
        ])
        if result.exit_code != 0: print_result(result)
        assert result.exit_code == 0
    
        result = runner.invoke(value, ['myapp:dev:FOO', 'BAZ'])
        if result.exit_code != 0:  print_result(result)
        assert result.exit_code == 0

        result = runner.invoke(get, ['myapp:dev:FOO'])
        if result.exit_code != 0: print_result(result)
        assert result.exit_code == 0
        assert result.output == 'BAZ\n'

        result = runner.invoke(key, [
            'FOO', 'QUUX',
            '--app=myapp',
            '--env=prod'
        ])
        if result.exit_code != 0: print_result(result)
        assert result.exit_code == 0

        result = runner.invoke(get, ['myapp:prod:FOO'])
        if result.exit_code != 0: print_result(result)
        assert result.exit_code == 0
        assert result.output == 'QUUX\n'

        result = runner.invoke(value, ['FOO', 'ZAAP', '--all'])
        if result.exit_code != 0: print_result(result)
        assert result.exit_code == 0
