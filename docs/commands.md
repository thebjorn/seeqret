
# Commands

## `seeqret init`
Initialize a new vault for a user in the current directory.

This will create a subdirectory named `seeqret` containing three key files
and the database. If on windows the `SEEQRET` environment variable will be
set to point to this folder.

You will be asked for username and email. The username defaults to your
hostname-qualified identity, `user@host` (e.g. `bjorn@mypc`). This keeps
two machines with the same username distinct: each vault has its own key
pair, so when you get a new computer you introduce yourself as e.g.
`bjorn@newpc` and recipients can tell the new key from the old one.

The vault can not be located inside a repository or on a network drive for
security reasons.

## Identities

Vault owners and users are identified by `user@host` names. Everywhere a
command takes a username (`export --to`, `load -u`, `slack link`,
`send --to`, ...) you can pass either:

- the full qualified name (`bjorn@mypc`), or
- the bare username (`bjorn`) — accepted as long as it matches exactly one
  user. If it matches several (e.g. `bjorn@oldpc` and `bjorn@newpc`),
  seeqret refuses to guess and lists the candidates.

Vaults created before hostname qualification simply have bare usernames;
they keep working unchanged. The key fingerprint remains the actual source
of truth — `user@host` is human-friendly disambiguation.

## ``seeqret add key``

```bash
$❱ seeqret add key NAME "VALUE" --app "*" --env "*"
```

`--app` and `--env` defaults to `"*"`.

Adding a key that already exists in the given `app:env` will fail by
default. Pass `--force` to overwrite the existing value in place:

```bash
$❱ seeqret add key NAME "NEW_VALUE" --app myapp --env dev --force
```

## `seeqret list [FILTERSPEC]`

List the contents of the vault, optionally only the secrets matching
FILTERSPEC (see [Filter spec](filter-strings.md)).

```bash
$❱ seeqret list myapp:prod:
$❱ seeqret list ":dev:POSTGRES_*" --env     # .env file format
```

`-f FILTERSPEC` is still accepted for backward compatibility.

## `seeqret get FILTER`

Print the value of a single secret.

```bash
$❱ seeqret get myapp:prod:DB_PASSWORD
```

Fails if FILTER matches no secret, or more than one. From Python use
`seeqret.get()` instead (see [Python API](python-api.md)).

## `seeqret add user`

```bash
$❱ seeqret add user
```
Add a user to the database. You can only export secrets to known users.

You will be prompted for username (`--username`), email (`--email`), and
the user's public key (`--pubkey`).

Record the username exactly as the other user presents it — the easiest
way is to have them run `seeqret introduction`, which prints a complete
`seeqret add user --username bob@hispc --email ... --pubkey ...` command
you can paste directly.

## `seeqret users`

List known users.

## `seeqret rm user USERNAME`

Remove a user from the vault.

```bash
$❱ seeqret rm user bob@hispc
```

`USERNAME` can be a bare or qualified name (see [Identities](#identities));
a bare name is accepted when it matches exactly one user. You will be
shown the user and asked to confirm; pass `--yes` to skip the prompt.

The vault owner cannot be removed.

## `seeqret export --to USER`

Create an export file that can be sent to "bob"
```bash
$❱ seeqret export --to bob
```

`bob` can be a bare or qualified username (see [Identities](#identities));
a bare name is accepted when it matches exactly one user.

Create an export file for yourself (useful for moving the vault to a
new computer/server).
```bash
$❱ seeqret export --to self
```

Export to every other known user in one go with `--to all`:
```bash
$❱ seeqret export --to all -f myapp:prod:
```

`all` expands to all known users except the vault owner. It can be
combined with other `--to` values; duplicate recipients are removed.

## `seeqret export users --to USER`

Send the users in your vault (usernames, emails and public keys) to
another user, e.g. to get a new team member's vault up to date:
```bash
$❱ seeqret export users --to bob -o users.json
```

The user list is encrypted to `bob` and authenticated with your key, so
`bob` knows the public keys came from you. `bob` imports it with
`seeqret load`:
```bash
$❱ seeqret load -u alice -f users.json
```

Users that already exist in `bob`'s vault are skipped. If one of them has
a different public key than in the export, `load` prints a warning and
keeps the existing key. `--to` accepts the same values as
`seeqret export --to` (including `all`); `-o` needs a single recipient.


## `seeqret load`

Load exported secrets into the local vault. This only works if you are the
intended recipient.

```bash
$❱ seeqret load -u alice -f export.json
$❱ seeqret load -u alice -v '<exported-value>' -s command
```

`load` also imports a `seeqret export users` file (see above).

The sender (`-u`) can be given as a bare or qualified username (see
[Identities](#identities)).

If an incoming secret has the same `app:env:key` as one already in the
vault, the existing value is **overwritten** with the imported one. This
makes `seeqret load` safe to re-run when the sender ships an updated
value for a secret you already have.


## `seeqret remote add ALIAS USERHOST`

Register a host you can push secrets to (and pull/verify from) over ssh.
`--set` is the remote command that stores a secret, `--get` (optional) the
one that prints it:

```bash
$❱ seeqret remote add myhost myuser@myhost.example.com \
       --set ". /srv/venv/myvenv/bin/activate && myvault set-secret --key {key} --stdin" \
       --get "... myvault get-secret --key {key} --stdout"
```

`{key}` and `{value}` are substituted shell-quoted, so don't quote them
yourself. Without a `{value}` placeholder the value is piped on stdin, which
keeps it off the remote command line.

`seeqret remote list` shows the registered remotes, `seeqret remote rm ALIAS`
removes one. Each remote becomes a sub-command of `push`, `pull` and
`verify`.

## `seeqret push TARGET [FILTERSPEC]`

Copy the secrets matching FILTERSPEC to an external system. TARGET is
`vercel` or a registered ssh remote; several remotes can be given
comma-separated.

```bash
$❱ seeqret push myhost myapp:prod:*
$❱ seeqret push web1,web2 myapp:prod:* --dry-run
$❱ seeqret push vercel myapp:prod:* --target production
```

`push vercel` needs the Vercel CLI and a linked project (`vercel link`).
Its `--target` (production, preview, development) is required, so a push
never reaches an environment you did not name. Existing variables with the
same name are overwritten.

## `seeqret pull REMOTE KEY...`

Fetch KEYs from an ssh remote (using its `--get` command) into the vault.
Values are never printed.

```bash
$❱ seeqret pull myhost DB_PASSWORD API_TOKEN --app myapp --env prod
```

`--app`/`--env` choose where the secrets are stored (default `*`).
Existing secrets are only overwritten with `--force`.

## `seeqret verify TARGET [FILTERSPEC]`

Check that an external system has the same values as the vault. Only key
names and `ok`/`MISSING`/`MISMATCH` are printed, never values.

```bash
$❱ seeqret verify myhost myapp:prod:*
$❱ seeqret verify vercel myapp:prod:* --target production
```

`verify vercel` defaults to `--target development`.

## `seeqret upgrade`

Upgrade the database to the latest version.

---

## Top level help
```bash
seeqret❱ seeqret --help
Usage: seeqret [OPTIONS] COMMAND [ARGS]...

Options:
  --version       Show the version and exit.
  -L, --log TEXT
  -h, --help      Show this message and exit.

Commands:
  add           Add a new secret.
  backup        Back up the vault to a password-protected HTML file.
  edit          Edit a secret or user in the vault.
  env           Read filters from env.template and export values from the...
  export        Export the vault TO a user (use `seeqret load` to import)
  get           Get the value of a secret (specified by FILTER).
  importenv     Import secrets from a .env file.
  info          List hierarchical command structure.
  init          Initialize a new vault in DIR
  introduction  Print an introduction to the vault.
  list          List the contents of the vault
  load          Save exported secrets to local vault.
  owner         List the owner of the vault
  public-key    Show the admin's public key.
  pull          Pull secrets from external systems into the vault.
  push          Push secrets from the vault to external systems.
  receive       Receive and import encrypted secrets from a transport.
  remote        Manage ssh remote targets for push/verify.
  rm            Remove a secret or user from the vault.
  send          Send encrypted secrets to a user via file or Slack.
  serializers   List available serializers.
  server        Server commands.
  setenv        Set global environment variables from secrets matching...
  slack         Slack-based secret exchange transport.
  upgrade       Upgrade the database to the latest version
  users         List the users in the vault
  verify        Verify that vault secrets match external systems.
  whoami        Display the current user and their role in the vault.
```

## add sub-commands
```bash
seeqret❱ seeqret add --help
Usage: seeqret add [OPTIONS] COMMAND [ARGS]...

  Add a new secret.

Options:
  -h, --help  Show this message and exit.

Commands:
  key   Add a new NAME -> VALUE mapping.
  text  Add a new multi-line secret with key NAME, eg recovery codes.
  user  Add a new user to the vault from a public key.
```
