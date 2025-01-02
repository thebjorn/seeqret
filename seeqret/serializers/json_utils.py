
# def _validate_import_file(indata):
#     """Validate json input.
#     """
#     errors = False
#
#     # don't abort early, we want the user to receive _all_ the errors.
#     if 'from' not in indata:
#         click.secho('Invalid file format, missing "from"', fg='red')
#         errors = True
#     if 'username' not in indata['from']:
#         click.secho('Invalid file format, missing "from.username"', fg='red')
#         errors = True
#     if 'email' not in indata['from']:
#         click.secho('Invalid file format, missing "from.email"', fg='red')
#         errors = True
#     if 'pubkey' not in indata['from']:
#         click.secho('Invalid file format, missing "from.pubkey"', fg='red')
#         errors = True
#     if 'data' not in indata:
#         click.secho('Invalid file format, missing "data"', fg='red')
#         errors = True
#     if 'signature' not in indata:
#         click.secho('Invalid file format, missing "signature"', fg='red')
#         errors = True
#     if 'to' not in indata:
#         click.secho('Invalid file format, missing: "to"', fg='red')
#         errors = True
#     if 'username' not in indata['to']:
#         click.secho('Invalid file format, missing "to.username"', fg='red')
#         errors = True
#
#     return not errors
#
#
# def ximport_secrets(indata):
#     """seeqret import-file <fname:json>
#     """
#     if not _validate_import_file(indata):
#         click.secho('Invalid file format.', fg='red')
#         return
#     click.secho("file format ok...", fg='green')
#
#     signature = indata['signature']
#     data = indata['data']
#     from_user = indata['from']
#     to_user = indata['to']['username']
#
#     cn = sqlite3.connect('seeqrets.db')
#     admin = fetch_admin(cn)
#     if to_user != admin['username']:
#         click.secho(
#             f'Incorrect to.username {to_user}, not {admin["username"]}',
#             fg='red'
#         )
#         return
#     click.secho("Correct `to` field.")
#
#     # cipher = load_symetric_key('seeqret.key')
#     sender_pubkey = public_key(from_user['pubkey'])
#     receiver_private_key = load_private_key('private.key')
#     for item in data:
#         item['val'] = asymetric_decrypt_string(item['val'],
#                                                receiver_private_key,
#                                                sender_pubkey)
#
#     click.secho("verifying signature...")
#     verify_hash(signature, indata)
#     click.secho('Successfully validated file', fg='green')
#
#     if not fetch_user(cn, from_user['username']):
#         add_user(
#             from_user['pubkey'],
#             from_user['username'],
#             from_user['email']
#         )
#     else:
#         click.secho('Found sender', fg='green')
#     cn.close()
#
#     # click.echo(json.dumps(indata, indent=4))
#
#     for secret in data:
#         add_key(
#             secret['key'],
#             secret['val'],
#             secret['app'],
#             secret['env'],
#             # secret['type']
#         )
#
#
# def verify_hash(hash: str, message):
#     msg = _extract_data(message)
#     h = hash_message(msg.encode('utf-8'))
#     if hash != h:
#         msg = f'Invaolid hash ({hash}) expected: {h}'
#         ctx = None
#         try:
#             ctx = click.get_current_context()
#         except RuntimeError:
#             pass
#         if ctx is not None:
#             ctx.fail(click.style(msg, fg='red'))
#         else:
#             raise RuntimeError(msg)
#     return True
#
#
# def _extract_data(message):
#     """Extract all message values (so they can be hashed)
#     """
#     data = []
#     for secret in message['data']:
#         data.append(f"{secret['app']}:{secret['env']}:{secret['key']}:{secret['val']}\n")  # noqa
#     data.sort()
#     sender = message['from']
#     data.append(
#         f'From:{sender["username"]}|{sender["email"]}|{sender["pubkey"]}\n'
#     )
#     data.append(f'To:{message["to"]["username"]}\n')
#     msg = ''.join(data)
#     return msg
#
