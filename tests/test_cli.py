# import os
#
# from click.testing import CliRunner
# from pathlib import Path
#
# from seeqret import seeqret_init, cd
# from seeqret.main import (
#     init,
#     list,
#     users,
#     user,
#     key,
# )
# from seeqret.utils import run
#
#
# def test_cli(monkeypatch):
#     runner = CliRunner()
#
#     with runner.isolated_filesystem():
#         tdir = Path(os.getcwd())
#         monkeypatch.setenv('SEEQRET', str(tdir / 'seeqret'))
#         init(str(tdir), 'test', 'test@example.com')
#
#         with cd(tdir):
#             print("TDIR:", tdir)
#             print("CURDIR:", os.getcwd())
#             assert tdir == Path(os.getcwd())
#
#             # result = runner.invoke(init, [
#             #     tdir,
#             #     # '--url', 'https://raw.githubusercontent.com/tkbeorg/tkbe/refs/heads/main/public.key',
#             #     '--user', 'test',
#             #     '--email' 'test@example.com',
#             # ])
#             # print("INIT:OUTPUT:", result.output)
#             run('tree .')
#             # assert listdir contains seeqret
#
#             # print("LIST:", os.path.listdir(tdir / 'seeqret')
#
#             result = runner.invoke(list)
#             assert result.output.strip() == ''
#
#             result = runner.invoke(users)
#             assert len(result.output) == 42
#             print("CLIRUNNER:OUTPUT:", result.output)
#             # print("CLIRUNNER:EXIT:CODE:", result.exit_code)
#             assert 'test@example.com (admin)' in result.output
#
#             result = runner.invoke(user,[
#                 '--username', 'tkbe',
#                 '--email', 'bjorn@tkbe.org',
#                 '--url', 'https://raw.githubusercontent.com/tkbeorg/tkbe/refs/heads/main/public.key'
#             ])
#             assert 'bjorn@tkbe.org' in result.output
#
#             result = runner.invoke(users)
#             assert len(result.output) == 42
#             assert 'bjorn@tkbe.org' in result.output
#
#             result = runner.invoke(key, [
#                 'FOO', 'bar'
#             ])
#             assert 'FOO' in result.output
