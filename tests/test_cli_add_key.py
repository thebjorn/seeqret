from click.testing import CliRunner

from seeqret.db_utils import debug_fetch_users, debug_secrets
from seeqret.main import cli, user, users, init, list, get
from seeqret.cli_group_add import key, text as add_text
from seeqret.storage.get_secret import get_secret
from tests.clirunner_utils import print_result


def test_add_key():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        result = runner.invoke(init, [
            '.',
            '--user=test',
            '--email=test@example.com',
        ])
        if result.exit_code != 0: print_result(result)
        assert result.exit_code == 0

        assert len(debug_secrets()) == 0
        result = runner.invoke(list)
        assert result.exit_code == 0
        assert len(debug_fetch_users()) == 1
        
        result = runner.invoke(key, [
            'FOO', 'BAR',
            '--app=myapp',
            '--env=dev'
        ])
        if result.exit_code != 0: print_result(result)
        assert result.exit_code == 0
        assert len(debug_secrets()) == 1

        result = runner.invoke(get, ['myapp:dev:FOO'])
        if result.exit_code != 0: print_result(result)
        assert result.exit_code == 0
        assert result.output == 'BAR\n'



def test_add_text():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        result = runner.invoke(init, [
            '.',
            '--user=test',
            '--email=test@example.com',
        ])
        if result.exit_code != 0: print_result(result)
        assert result.exit_code == 0

        text_input = '1234567890\n1234567890\n1234567890\n'

        result = runner.invoke(add_text, [
            'FOO',
            '--app=myapp',
            '--env=dev'
        ], input=text_input + '\x04')  # add EOF
        if result.exit_code != 0: print_result(result)
        assert result.exit_code == 0

        result = runner.invoke(get, ['myapp:dev:FOO'])
        if result.exit_code != 0: print_result(result)
        assert result.exit_code == 0
        assert result.output == text_input + '\n'


# def test_add_file():
#     runner = CliRunner(env=dict(TESTING="TRUE"))
#     with runner.isolated_filesystem():
#         result = runner.invoke(init, [
#             '.',
#             '--user=test',
#             '--email=test@example.com',
#         ])
#         if result.exit_code != 0: print_result(result)
#         assert result.exit_code == 0

#         with open('test.txt', 'w') as f:
#             f.write('a = "1234567890"\nb = "1234567890"\nc = "1234567890"')

#         result = runner.invoke(add_env, [
#             'test.txt',
#             '--app=myapp',
#             '--env=dev'
#         ])
#         if result.exit_code != 0: print_result(result)
#         assert result.exit_code == 0

#         print("DEBUG_SECRETS", debug_secrets())
#         result = runner.invoke(get, ['myapp:dev:a'])
#         if result.exit_code != 0: print_result(result)
#         assert result.exit_code == 0
#         assert result.output == '1234567890'
