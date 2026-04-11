# Slack Exchange Implementation Plan (Python seeqret)

## Context

This plan is the Python counterpart to the jseeqret plan at
`e:\work\jseeqret\documentation\slack-exchange\PLAN.md`. The two
implementations must stay compatible on the wire: a ciphertext blob
posted by the Python CLI must be decryptable by the JavaScript CLI and
vice versa, because both tools share the same NaCl keys, Fernet keys,
and SQLite schema. The security posture is identical -- all nine
concerns in `../slack-exchange/security-concerns.md` (if mirrored into
this repo) or the jseeqret copy are treated as hard requirements.

Test team: `ntseeqrets`. Test channel: `#seeqrets` (private).

## Guiding Principles (mapped to security-concerns.md)

| # | Concern                            | Enforcement                                                                                                    |
| - | ---------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| 1 | Third-party ciphertext custody     | `send` refuses non-ciphertext; delete-on-import                                                                |
| 2 | Metadata leakage                   | Opaque filename `jsenc-<uuid>.bin`; 4 KiB bucket padding; thread text is only `<@U...>`                        |
| 3 | Bot token = high-value secret      | User tokens via OAuth PKCE (not bot tokens); Fernet-encrypted in vault `kv` table under `slack.user_token`     |
| 4 | Handle to pubkey binding           | `seeqret slack link` requires manual fingerprint confirmation; cached on the `users` row; mismatch = refuse    |
| 5 | Account takeover = inbox takeover  | All exports are NaCl Box (sender-authenticated); `receive` rejects unknown senders                             |
| 6 | Retention vs forward secrecy       | `receive` deletes Slack message + file after successful import; `slack doctor` fails if retention > 24 h      |
| 7 | DLP / connected-app mirroring      | `slack doctor` hashes the connected-app list; drift requires explicit `--accept`                              |
| 8 | Rate limits / availability         | Backoff on 429; `receive` fails closed on any API error                                                        |
| 9 | Legal discovery of metadata        | Documented in the per-team setup section                                                                       |

## Critical Files

### New (core)

- `seeqret/slack/__init__.py`
- `seeqret/slack/client.py`    -- thin wrapper around `slack_sdk.WebClient`
  with injected token and 429 backoff. Exposes `auth_test`,
  `files_upload_v2`, `files_delete`, `conversations_history`,
  `conversations_replies`, `chat_post_message`, `chat_delete`,
  `users_lookup_by_email`, `apps_connections_list`.
- `seeqret/slack/transport.py` -- `send_blob(ciphertext, recipient_id)`,
  `poll_inbox(since_ts)`, `delete_message(ts, file_id)`.
- `seeqret/slack/identity.py`  -- fingerprint-verified pubkey to
  Slack handle mapping; reads/writes new columns on `users`.
- `seeqret/slack/config.py`    -- channel_id, last_seen_ts, OAuth tokens
  persisted Fernet-encrypted in the new `kv` table.
- `seeqret/slack/oauth.py`     -- OAuth v2 PKCE flow using a
  `http.server.BaseHTTPRequestHandler` loopback listener on
  `http://127.0.0.1:<ephemeral>/callback`.
- `seeqret/slack/padding.py`   -- 4 KiB bucket padding with a 4-byte
  length prefix (must be byte-compatible with jseeqret's implementation
  so blobs cross between CLIs).

### New (CLI -- in `seeqret/main.py`)

- `@cli.group('slack')` with subcommands:
  - `slack login`
  - `slack logout`
  - `slack link <handle>`
  - `slack doctor [--accept]`
  - `slack status`
- `@cli.command('send')` -- `send <filter>... --to <user> [--via slack|file]`.
  `--via file` is a thin alias around the existing `export` command.
- `@cli.command('receive')` -- `receive [--via slack] [--watch] [--interval <s>]`.

### Modified

- `seeqret/main.py` -- register the new groups and commands.
- `seeqret/migrations/db_v_003.py` -- new migration with the schema
  changes below. (Numbering follows existing `db_v_001.py` pattern; if
  there is already a `db_v_002.py`, advance accordingly.)
- `setup.py` -- add `slack-sdk` to `install_requires`.

### Reused (do NOT reimplement)

- `seeqret/seeqrypt/nacl_backend.py`
  - `asymetric_encrypt_string`, `asymetric_decrypt_string`, `fingerprint`
- `seeqret/seeqrypt/utils.py`
  - `load_symetric_key`, `encrypt_string`, `decrypt_string` for the
    Fernet wrap of Slack tokens and channel config
- `seeqret/storage/sqlite_storage.py` -- extended, not replaced
- `seeqret/models/user.py` -- extended with new columns (kept backward
  compatible by letting the new fields default to `None`)
- `seeqret/run_utils.py` -- `get_seeqret_dir`, `seeqret_dir` context
  manager, `is_initialized`

## Data Model Changes

Migration `db_v_003.py` (new file, follows the pattern of
`db_v_001.py`):

```sql
ALTER TABLE users ADD COLUMN slack_handle TEXT;
ALTER TABLE users ADD COLUMN slack_key_fingerprint TEXT;
ALTER TABLE users ADD COLUMN slack_verified_at INTEGER;

CREATE TABLE IF NOT EXISTS kv (
    key             TEXT PRIMARY KEY,
    encrypted_value BLOB NOT NULL,
    updated_at      INTEGER NOT NULL
);
```

The schema must match the jseeqret migration byte-for-byte so both tools
see the same columns. `kv` key names (all Fernet-encrypted):

- `slack.user_token`          -- `xoxp-...` OAuth user token
- `slack.team_id`
- `slack.team_name`
- `slack.channel_id`
- `slack.channel_name`         -- e.g. `seeqrets`
- `slack.last_seen_ts`         -- ts of the last successfully imported blob
- `slack.connected_apps_hash`  -- baseline hash for `slack doctor`

## Wire Protocol

Identical to the jseeqret plan. Each `seeqret send --via slack`
produces one `files.uploadV2` call and one thread reply:

1. **File upload**
   - `filename`: `jsenc-<uuid4>.bin`
   - `title`: empty string
   - `content`: ciphertext bytes padded to the nearest 4 KiB bucket,
     with a 4-byte big-endian length prefix so the receiver can strip
     the padding
   - `channels`: configured `channel_id`
2. **Thread reply**
   - Body: `<@U_BOB>` only -- no filenames, no `app:env:key`, no commentary

`receive` walks `conversations.history` forward from `last_seen_ts`:

1. Fetch the thread; match the `<@U...>` mention against `auth_test.user_id`
2. Download the file via `files.info` (Bearer auth on the private URL)
3. Strip padding, `asymetric_decrypt_string` against the sender's known
   NaCl pubkey (resolved via `users.slack_handle`)
4. On success: `storage.add_secret` per entry, then `files.delete` and
   `chat.delete` on the thread reply
5. Advance `last_seen_ts` **only** after deletes return OK
6. On any failure: fail closed, exit non-zero, do not advance state

## CLI Surface

```
seeqret slack login                               # OAuth + channel picker
seeqret slack logout                              # wipes slack.* kv entries
seeqret slack link <handle>                       # fingerprint-verified binding
seeqret slack doctor [--accept]                   # retention + connected-apps + scopes
seeqret slack status                              # team, channel, last_seen_ts, token age

seeqret send <filter>... --to <user> --via slack
seeqret receive --via slack [--watch] [--interval <s>]
```

## OAuth and Identity Flow

### `seeqret slack login`

1. Bind a `http.server.HTTPServer` to `('127.0.0.1', 0)` to grab an
   ephemeral port.
2. Build the authorize URL with PKCE `code_challenge` and
   `redirect_uri=http://127.0.0.1:<port>/callback`.
3. `webbrowser.open(authorize_url)` and block on the single-request
   handler until Slack redirects back with `code`.
4. Exchange `code` + `code_verifier` via `oauth.v2.access` for a User
   token. Tokens are stored Fernet-encrypted in `kv`.
5. `auth.test` -> store `team_id`, `team_name`, `user_id`.
6. List the private channels the user is a member of
   (`conversations.list` with `types=private_channel`); prompt to pick
   one (default `seeqrets`); persist `channel_id` and `channel_name`.

### `seeqret slack link <handle>`

1. Look up `<handle>` in the local `users` table (must already exist
   via `seeqret add user`).
2. Resolve the Slack `user_id` via `users.lookupByEmail` (fallback
   `users.list`).
3. Print the local pubkey fingerprint (via
   `nacl_backend.fingerprint(user.public_key.encode())`):
   `Local pubkey fingerprint: ab12c`
4. Prompt:
   `Type "ab12c" to confirm you have verified this fingerprint with
   <handle> out-of-band (voice/in-person):`
5. On confirm, write `slack_handle`, `slack_key_fingerprint`, and
   `slack_verified_at` on the users row.
6. On every later `send --via slack --to <handle>`: recompute the
   fingerprint, refuse if it no longer matches.

Public keys are never fetched from Slack profiles or pinned messages.

## Setup Instructions

### For the seeqret maintainer (one-time)

Same as the jseeqret plan: the Slack app is pre-registered and its
Client ID (plus a non-sensitive Client Secret used in the PKCE user-token
flow) is baked into the Python package. Scopes are **User Token Scopes**
only:

- `channels:history`, `channels:read`
- `files:read`, `files:write`
- `chat:write`, `chat:write:user`
- `users:read`, `users:read.email`

Redirect URL: `http://127.0.0.1/callback`. No Socket Mode, no
App-Level tokens.

Because jseeqret and Python seeqret ship the same Slack app, **only one
app needs to be registered total**. Both CLIs use the same Client ID.
Revocation of the app therefore affects both clients simultaneously.

### For each team admin (one-time per team)

1. Create the Slack team (`ntseeqrets` for testing).
2. Enforce SSO + hardware MFA at the workspace level.
3. Create private channel `#seeqrets`, add every sender/receiver.
4. Set channel retention on `#seeqrets` to 24 hours.
5. Audit connected apps. Remove anything with `files:read` on the
   exchange workspace (DLP, archivers, e-discovery).
6. Keep the workspace scoped narrowly for legal-discovery hygiene.

### For each user (one-time per vault)

```bash
seeqret slack login             # opens browser
seeqret slack doctor            # must be all-green before first send
seeqret slack link alice        # confirm fingerprint over voice
seeqret slack link carol
```

### Ongoing hygiene (`seeqret slack doctor`)

Same checklist as jseeqret:

- User token present and not older than 90 days
- Channel retention <= 24 h
- No archiver/DLP app has `files:read`
- Connected-app list unchanged since last accepted baseline (warn once,
  then hard-fail until `seeqret slack doctor --accept`)
- Every linked user has a fingerprint verified in the last 180 days
- SSO + hardware MFA attestation (manual, re-prompted every 90 days)

`send` and `receive` refuse to run while doctor is in fail state.

## Build Sequence

1. **Migration + `kv` helpers** in `SqliteStorage`
   (`kv_get`, `kv_set`, `kv_delete`). Fernet wrap/unwrap lives in
   `seeqret/slack/config.py`. Unit tests for round-trip under `tests/`.
2. **`seeqret/slack/client.py`** -- `slack_sdk.WebClient` wrapper with
   injected token and 429 backoff.
3. **`seeqret/slack/oauth.py`** + `slack login` command. Manual test
   against `ntseeqrets`.
4. **`seeqret/slack/identity.py`** + `slack link`. Unit tests for both
   the correct-fingerprint and wrong-fingerprint paths.
5. **`seeqret/slack/transport.py`** + `seeqret/slack/padding.py`.
   Unit tests with a `slack_sdk` mock and a round-trip padding test
   cross-checked against jseeqret's fixture vectors.
6. **`send` / `receive` commands** wired into the existing
   `export`/`load` pipeline; delete-on-import; `last_seen_ts`
   bookkeeping.
7. **`slack doctor`** with all checks.
8. **End-to-end test** against `ntseeqrets` / `#seeqrets`: alice to bob
   loop (in both directions -- Python send to JavaScript receive and
   vice versa, to prove cross-implementation compatibility).
9. **Docs**: this PLAN.md, a `documentation/slack-exchange/index.md`
   and `security-concerns.md` copy, README entry.

## Resolved Decisions (shared with jseeqret)

- Slack app credentials baked into the package -- no per-team app.
- `receive --watch` uses polling only in the MVP. Default 30 s,
  `--interval` overrides.
- `slack doctor` warn-once-then-fail on connected-app drift;
  `--accept` re-baselines.
- NaCl Box authentication is sufficient; no extra detached signature.

## Verification

1. `pytest tests/test_slack_*.py` -- unit tests for transport (mocked
   `WebClient`), identity binding, `kv` round-trip, padding.
2. On a second dev vault:
   - `seeqret slack login` -> OAuth succeeds
   - `seeqret slack doctor` -> all green
   - `seeqret slack link alice` with a wrong confirmation -> refused
   - `seeqret slack link alice` with the correct fingerprint -> stored
3. Alice: `seeqret send '*:*:test_key' --to bob --via slack`; inspect
   the channel in a browser.
4. Bob: `seeqret receive --via slack`; verify the secret lands, the
   Slack file and thread reply are gone, and `last_seen_ts` advanced.
5. Replay `receive` -> no-op.
6. Tamper with a blob mid-flight -> `receive` exits non-zero, vault
   unchanged.
7. **Cross-implementation**: `jseeqret send --via slack` to a Python
   `seeqret receive --via slack` (and the reverse). Both must succeed
   and delete the message.
8. Raise retention above 24 h -> `slack doctor` fails, `send` refuses.
9. Install a harmless workspace app -> `slack doctor` warns once; run
   again without `--accept` -> hard-fails.
