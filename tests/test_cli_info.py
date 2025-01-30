import re
import sys

from click.testing import CliRunner
from seeqret.main import cli, init, info
from seeqret.migrations.utils import current_version


def test_info():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        result = runner.invoke(info)
        assert result.exit_code == 0
