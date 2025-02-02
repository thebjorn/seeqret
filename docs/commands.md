
# Commands

## `seeqret init`
Initialize a new vault for a user in the current directory.

This will create a subdirectory named `seeqret` containing three key files
and the database. If on windows the `SEEQRET` environment variable will be
set to point to this folder.

You will be asked for username and email.

The vault can not be located inside a repository or on a network drive for
security reasons.

## ``seeqret add key``

```bash
$❱ seeqret add key NAME "VALUE" --app "*" --env "*"
```

`--app` and `--env` defaults to `"*"`.

## `seeqret list`

List the contents of the vault.

## `seeqret add user`

```bash
$❱ seeqret add user
```
Add a user to the database. You can only export secrets to known users.

You will be prompted for username (`--username`), email (`--email`), and
the url (`--url`) where the user's public key is located.

**TODO:** add `--pubkey` flag.

## `seeqret users`

List known users.

## `seeqret export TO`

Create an export file that can be sent to "bob"
```bash
$❱ seeqret export bob
```

Create an export file for yourself (useful for moving the vault to a
new computer/server).
```bash
$❱ seeqret export self
```


## `seeqret import FNAME`

Import an export file. Will only work if you are the intended receipient.


## `seeqret upgrade`

Upgrade the database to the latest version.

---

## Top level help
```bash
seeqret❱ seeqret --help
Usage: seeqret [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  add          Add a new secret, key or user
  export       Export the vault to a user
  import-file  Import a vault from a file
  init         Initialize a new vault
  list         List the contents of the vault
  upgrade      Upgrade the database to the latest version
  users        List the users in the vault
```

## add has two sub-commands
```bash
seeqret❱ seeqret add --help                                                                                                                                                                              seeqret   
Usage: seeqret add [OPTIONS] COMMAND [ARGS]...

  Add a new secret, key or user

Options:
  --help  Show this message and exit.

Commands:
  key   Add a new key/value pair.
  user  Add a new user to the vault from a public key.
```
