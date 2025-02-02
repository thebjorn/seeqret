import re
import sys

from click.testing import CliRunner
from seeqret.main import cli, init, info
from seeqret.migrations.utils import current_version
from tests.clirunner_utils import print_result


def test_info():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        result = runner.invoke(info)
        if result.exit_code != 0:  print_result(result)
        assert result.exit_code == 0

        result = runner.invoke(info, ['--dump'])
        if result.exit_code != 0:  print_result(result)
        assert result.exit_code == 0
