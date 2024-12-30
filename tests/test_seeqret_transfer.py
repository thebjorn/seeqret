# from click.testing import CliRunner
#
# from seeqret.db_utils import debug_fetch_users, debug_secrets
# from seeqret.main import cli, user, users, init, list, key
# from tests.clirunner_utils import print_result
# from seeqret.seeqret_transfer import hash_secrets_message, verify_hash
#
#
# def test_hash():
#     runner = CliRunner(env=dict(TESTING="TRUE"))
#     msg = {
#         "data": [
#             {
#                 "app": "yerbu",
#                 "env": "dev",
#                 "key": "LANGCHAIN_API_KEY",
#                 "val": "12345"
#             }
#         ],
#         "from": {
#             "username": "bp",
#             "email": "bp@norsktest.no",
#             "pubkey": "ThkU/1VYhO723bGIYDrPUjczkgNEIsgQLa2R83oYNmQ="
#         },
#         "to": {
#             "username": "bp"
#         }
#     }
#     h = hash_secrets_message(msg)
#     print(h)
#     assert h == 'ugIEK38KzyfbYO3vsoNVCnJdofBel5ttPOnhoh8VCJ8='
#     assert verify_hash(h, msg)
