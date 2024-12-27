from click.testing import CliRunner

from seeqret.db_utils import debug_fetch_users
from seeqret.main import cli, user, users, init
from tests.clirunner_utils import print_result


def test_add_user():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        result = runner.invoke(init, [
            '.',
            '--user=test',
            '--email=test@example.com',
        ])
        assert result.exit_code == 0

        result = runner.invoke(users)
        assert result.exit_code == 0
        assert 'test@example.com' in result.output

        # print("DBUSERS:", debug_fetch_users())
        assert len(debug_fetch_users()) == 1
        result = runner.invoke(user,[
            '--username=tkbe',
            '--email=bjorn@tkbe.org',
            '--url=https://raw.githubusercontent.com/tkbeorg/tkbe/refs/heads/main/public.key'
        ])
        # print_result(result)
        print("DBUSERS:", debug_fetch_users())
        #
        assert len(debug_fetch_users()) == 2
        # print(result.output)
        assert result.exit_code == 0

        assert 'bjorn@tkbe.org' in result.output
        # assert 'test@example.com' in result.output

        # assert len(result.output) == 42

        # result = runner.invoke(user, [
        #     '--url='
        # ])
