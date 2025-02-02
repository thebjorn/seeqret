# import os
# import sqlite3
#
# from click.testing import CliRunner
#
# from seeqret.db_utils import debug_fetch_users
# from seeqret.main import cli, init, key
# from seeqret.serializers.insecure_json import InsecureJsonSerializer
# from seeqret.storage.sqlite_storage import SqliteStorage
#
#
# def test_insecure_json(caplog):
#     import logging
#     caplog.set_level(logging.DEBUG)
#     runner = CliRunner(env=dict(TESTING="TRUE"))
#     with runner.isolated_filesystem() as directory:
#         result = runner.invoke(init, [
#             '.',
#             '--user=test',
#             '--email=test@example.com',
#         ])
#         assert result.exit_code == 0
#         result = runner.invoke(key, [
#             'FOO', 'BAR',
#             '--app=myapp',
#             '--env=dev'
#         ])
#         assert result.exit_code == 0
#         storage = SqliteStorage()
#         serializer = InsecureJsonSerializer()
#         data = serializer.serialize(storage)
#         print("SERIALIZED:", data)
#         res = serializer.deserialize(data)
#         assert res['users'][0]['username'] == 'test'
