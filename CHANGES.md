# CHANGES

API changes to seeqret. Use this to synchronize with
[jseeqret](https://github.com/thebjorn/jseeqret).

## Unreleased

- New `seeqret rm user USERNAME` command to remove a user from the
  vault. `USERNAME` can be a bare or qualified (`user@host`) name; a
  bare name is accepted when it matches exactly one user. The command
  shows the user and asks for confirmation (skip with `--yes`). The
  vault owner cannot be removed.
- `seeqret export --to` now accepts the special value `all`, which
  expands to every known user except the vault owner. It can be mixed
  with other `--to` values; duplicate recipients are removed.

## 0.4.2

- Vault owners and users are now identified by hostname-qualified
  usernames on the form `user@host`, e.g. `bjorn@mypc`
  ([#25](https://github.com/thebjorn/seeqret/issues/25)). This keeps the
  same username on two machines (each with its own key pair) distinct.
  - `seeqret init` defaults the username to `user@host` (previously the
    `USERNAME` environment variable).
  - Commands that take a username (`export --to`, `load -u`,
    `slack link`, `send --to`) accept either the full qualified name or
    a bare username, as long as the bare name matches exactly one user.
    An ambiguous bare name fails with a list of the candidates.
  - Existing vaults with bare usernames keep working unchanged (lookups
    try the qualified identity first and fall back to the bare name).
- `setup.py` reads README.md as utf-8 (fixes `pip install` on Windows
  when the default codepage is cp1252).
- Refreshed README and command reference docs (identity format, current
  `export --to` syntax, up-to-date command listings).

## 0.4.1

- New `seeqret push vercel` command to push secrets to a linked Vercel
  project.

## 0.4.0

- `seeqret load` now **overwrites** an existing secret with the imported
  value when the incoming secret has the same `app:env:key`, making it
  safe to re-run when the sender ships an updated value.

## 0.3.10

- New Slack-based secret exchange transport: `seeqret slack
  login/link/status/doctor/logout` plus `seeqret send` and
  `seeqret receive` for NaCl-encrypted secret blobs.
- `seeqret add key --force` overwrites an existing value in place
  (adding an existing key still fails by default).

## 0.3.9

- `seeqret list` now accepts an optional positional filterspec argument.
  `seeqret list yerbu:prod:` is equivalent to `seeqret list -f yerbu:prod:`.
  The `-f`/`--filter` flag is still supported for backward compatibility.
  When both are provided, `-f` takes precedence.
