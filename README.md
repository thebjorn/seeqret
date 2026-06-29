
# Safely transferring code secrets
(very much a work in progress)

![cicd](https://github.com/thebjorn/seeqret/actions/workflows/ci.yml/badge.svg)
[![codecov](https://codecov.io/gh/thebjorn/seeqret/graph/badge.svg?token=5PQOZLTSYD)](https://codecov.io/gh/thebjorn/seeqret)
[![pypi](https://img.shields.io/pypi/v/seeqret?label=pypi%20seeqret)](https://pypi.org/project/seeqret/)
[![downloads](https://pepy.tech/badge/seeqret)](https://pepy.tech/project/seeqret)
[![Socket Badge](https://socket.dev/api/badge/pypi/package/seeqret/0.1.7?artifact_id=tar-gz)](https://socket.dev/pypi/package/seeqret/overview/0.1.7/tar-gz)
<a href="https://github.com/thebjorn/seeqret"><img src="docs/github-mark/github-mark.png" width="25" height="25"></a>


<img src="https://codecov.io/gh/thebjorn/seeqret/graphs/tree.svg?token=5PQOZLTSYD" width=160 style="float:right">

<img src="https://raw.githubusercontent.com/thebjorn/seeqret/master/docs/seeqret-logo-256.png?sanitize=true" style="margin-inline:auto;display:block">

<!-- vscode-markdown-toc -->
* [Introduction](#Introduction)
	* [Prior art...](#Priorart...)
* [Assumptions](#Assumptions)
* [Requirements](#Requirements)
* [Use cases](#Usecases)
* [Developer machine](#Developermachine)
* [add a key/value pair](#addakeyvaluepair)
* [list secrets](#listsecrets)
* [create a .env file](#createa.envfile)
* [export a secret to another user](#exportasecrettoanotheruser)
	* [first ask for the users personal info](#firstaskfortheuserspersonalinfo)
	* [add the user](#addtheuser)
	* [export the keys you want to send](#exportthekeysyouwanttosend)
	* [shortcut for transferring secrets](#shortcutfortransferringsecrets)
* [explore](#explore)
* [Server](#Server)

<!-- vscode-markdown-toc-config
	numbering=false
	autoSave=true
	/vscode-markdown-toc-config -->
<!-- /vscode-markdown-toc -->


# Seeqret: Safely transferring code secrets
(very much a work in progress)



## <a name='Introduction'></a>Introduction

How do you communicate the set of secrets (passwords, API keys, etc.) that your code needs to run? You can't just write them in the code, because that would expose them to anyone who can read the code. You can't just send them in an email, because that would expose them to anyone who can read your email. You can't just write them on a sticky note, because that would expose them to anyone who can read your sticky note.

### <a name='Priorart...'></a>Prior art...

There are many ways to store and use secrets, e.g.:

- **Environment variables**: It is popular, in e.g. kubernetes and javascript, to read secrets from environment variables. For development these are stored in .env files that are not checked into git/svn. These files contain the secrets in plain-text. Transferring secrets to a new server/devloper is a manual process where you create a new file and somehow get access to the secrets.

- **Key vaults**: E.g. Secureden or HashiCorp Vault (can be self hosted). These are usually expensive or complex to set up - or both. Key vaults usually have an API that you can use to get the secrets (setting this up is also expensive/complex/both).

- **Secret management services**: These are hosted key vaults, e.g. AWS Secrets Manager, Google Secret manager, Azure Key Vault, or hosted HashiCorp Vault. There is always an associated api to read the secrets. This can incur significant costs for large numbers of secrets and/or high usage.

- **Encrypted files**: This is usually a key/value file (.json/.yaml), where only the values are encrypted (e.g. [SOPS](https://github.com/getsops/sops). Every developer must have the same key to be able to use the file, but the file can be stored in git/svn.


# Seeqret
Seeqret stores "passwords", encrypted, in a sqlite database. On windows this database is stored in an encrypted folder
and permissions are removed from anyone but the developer.

A cli, `seeqret`, is provided to add/remove/edit/etc. the key/value pairs. 

When transferring secrets to another developer they are first encrypted with a public/private key-pair, thus ensuring
encryption both at rest and in transit.

An api is provided for use in Python (`seeqret.get("key")`). This api can do 7000+ fetches/sec on my machine, and 
is faster than a fixed record file format.

Please read and understand the docstring in `__init__.py` before using!

## <a name='Assumptions'></a>Assumptions
We make the following assumptions:

- https is secure
- the encryption algorithms are secure
- encrypted directories (Windows) are secure (`seeqret` will use the following receipe when setting up its data directory):
  ```bat
  attrib +I %1
  icacls %1 /grant %USERDOMAIN%\%USERNAME%:(F) /T
  icacls %1 /inheritance:r
  cipher /e %1
  ```
- [encrypted private directories](https://help.ubuntu.com/community/EncryptedPrivateDirectory) (Ubuntu) are secure.
- `0600` (read/write by owner only) directories (linux) are safe provided the user is not compromised.

# The following requirments and use-cases have guided the devlopment

## <a name='Requirements'></a>Requirements
1. different users/systems should have access to different subsets of the secrets.
2. the secrets should not exist in plain-text when they are not used (e.g. a
   database password is only _used_ when logging into the database - it shouldn't exist in memory outside of this process[^3]).
3. a subset of secrets needs to be **shared with new developers** in a secure way.
4. there should be a command line utility (`seeqret`) to
   - `seeqret add key <key> <value>`: set a secret
   - `seeqret get <key>`: get a secret
   - `seeqret export <user> <keys..>` export a subset of the secrets for transmission (e.g. by email) to a new developer
   - `seeqret import <keys..>` import keys received by e.g. email
5. and a library/API to
   - `seeqret.get(key)`: get a secret (this should be a fast O(1) operation)
5. the secrets should be easy to update[^1].
6. it should be possible to backup the secrets.
7. _(bonus)_: the secrets should be easy to rotate[^2].
8. _(bonus)_: the secrets should be auditable[^4].

## <a name='Usecases'></a>Use cases

1. **Starting from scratch:** How do you set up the secrets system?
2. **Inviting users:** How do you invite users and how do you communicate the secrets to them?
3. **Adding a secret:** How do you communicate a new secret to the users?
4. **Updating a secret:** How do you communicate an update to a secret?
5. **New user:** How does a new user get access to the secrets?
6. **Backup:** How do you backup the secrets and what is needed to restore the backup?
7. **Developer leaves:** How do you revoke access to the secrets for a developer that leaves?


# Installation and usage
You must have at least Python 3.10+ to run seeqret!

## <a name='Developermachine'></a>Developer machine
To install the vault under c:\home (the directory must _not be on a network drive_ or inside a version
controlled directory):

```bash
pip install seeqret
seeqret init c:\home --email <your-email>
seeqret users
```

Your identity defaults to `username@hostname` (e.g. `bjorn@mypc`), so the same
username on two machines (each with its own key pair) stays distinct. Commands
that take a username (`export --to`, `load --from-user`, `slack link`, ...)
accept the bare username as long as it only matches one user; if it is
ambiguous you'll be asked to use the full `user@host` form.

## <a name='addakeyvaluepair'></a>add a key/value pair

```bash
seeqret add key KEY secret --app=myapp --env=dev
```

## <a name='listsecrets'></a>list secrets

List all dev secrets that start with `POSTGRES_`:

```bash
seeqret list -f :dev:POSTGRES_*
```

See the filter docs for more info (https://thebjorn.github.io/seeqret/filter-strings/).

## <a name='createa.envfile'></a>create a .env file

```bash
❱ seeqret add key FOO bar --env dev                                               
Adding a new key: FOO, value: bar, app: *, env: dev
❱ cat env.template                                                                
# all FOO* keys from the dev environment
:dev:FOO*
❱ seeqret env                                                                     
FOO="bar"
Created .env file with 1 secrets
❱ cat .env                                                                        
FOO="bar"
```

## <a name='exportasecrettoanotheruser'></a>export a secret to another user

### <a name='firstaskfortheuserspersonalinfo'></a>first ask for the users personal info
Have the other user run
```bash
❱ seeqret owner                                                                   
┏━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ # ┃ username   ┃ email           ┃ publickey                                    ┃
┡━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 1 │ bjorn@mypc │ bp@norsktest.no │ MBiGKmtpckXspJkmijIPXd8GrIAgAdLOoM4pZNOyDzw= │
└───┴────────────┴─────────────────┴──────────────────────────────────────────────┘
```
and send the information to you (you should directly verify the public key).
They can also run `seeqret introduction`, which prints a ready-to-paste
`seeqret add user ...` command containing the same information.

### <a name='addtheuser'></a>add the user
Add the other user as a known person to your vault:

```bash
❱ seeqret add user -h                                                             
Usage: seeqret add user [OPTIONS]

  Add a new user to the vault from a public key.

Options:
  --username TEXT  Username to record
  --email TEXT     Email for the user
  --pubkey TEXT    Public key for the user
  -h, --help       Show this message and exit.

❱ seeqret add user --username bjorn@mypc --email bp@norsktest.no --pubkey MBiGKmtpckXspJkmijIPXd8GrIAgAdLOoM4pZNOyDzw=
...
```

### <a name='exportthekeysyouwanttosend'></a>export the keys you want to send

```bash
❱ seeqret export --to bjorn -f :dev:FOO                                                
{
    "from": {
        "email": "bp@norsktest.no",
        "pubkey": "MBiGKmtpckXspJkmijIPXd8GrIAgAdLOoM4pZNOyDzw=",
        "username": "bjorn@mypc"
    },
    "secrets": [
        {
            "app": "*",
            "env": "dev",
            "key": "FOO",
            "type": "str",
            "value": "W4Fuverw5Mw//ccvYVm40ysVdSxQ4ZwpNTkBuyXtPvtmIQLkd2cl9veG+w=="
        }
    ],
    "signature": "0e34f5934979a9deb02ab0c584b39a4d128188df36ec61a0d591ffd9e4e65f70",
    "to": {
        "email": "bp@norsktest.no",
        "pubkey": "MBiGKmtpckXspJkmijIPXd8GrIAgAdLOoM4pZNOyDzw=",
        "username": "bjorn@mypc"
    },
    "version": 1
}
```

Note that `--to bjorn` found the user `bjorn@mypc`: a bare username resolves
to the matching `user@host` user as long as there is exactly one match. If
you know `bjorn` on more than one machine, seeqret will refuse to guess and
list the candidates instead.

The other user can load this file with

```bash
> seeqret load -f message.json
```

**NOTE:** only the intended recipient can decrypt/load the file.

### <a name='shortcutfortransferringsecrets'></a>shortcut for transferring secrets

There `command` serializer makes it convenient to send a "few" secrets e.g. in chat:

```bash
❱ seeqret export --to bjorn -f :dev:FOO -s command                                     
seeqret load -ubjorn@mypc -scommand -v1::84efd:*:dev:FOO:str:jsPI3HbN7zLNpogELFbOYZaFR4wFGs2+f6m6ZJCQ2ey88fovih5ZHzIESg==
```

the recipient only has to copy and paste the command into their terminal to import the secret.

**NOTE:** only the intended recipient can import the secret with this command line.

## <a name='explore'></a>explore

List all commands:
```bash
> seeqret info
cli
    add                        Add a new secret.
        key                    Add a new NAME -> VALUE mapping.
        text                   Add a new multi-line secret with key NAME, eg recovery codes.
        user                   Add a new user to the vault from a public key.
    backup                     Backup the vault to a file.
    edit                       Edit a secret or user in the vault.
        value                  Update secrets matching FILTER to the new VALUE.
    env                        Read filters from env.template and export values from the vault to an .env file.
    export                     Export the vault TO a user (use `seeqret load` to import)
    get                        Get the value of a secret (specified by FILTER).
    importenv                  Import secrets from a .env file.
    info                       List hierarchical command structure.
    init                       Initialize a new vault in DIR
    introduction               Print an introduction to the vault.
    list                       List the contents of the vault
    load                       Save exported secrets to local vault.
    owner                      List the owner of the vault
    public-key                 Show the admin's public key.
    push                       Push secrets from the vault to external systems.
        vercel                 Push secrets matching FILTER to the linked Vercel project.
    receive                    Receive and import encrypted secrets from a transport.
    rm                         Remove a secret or user from the vault.
        key                    Remove a secret from the vault specified by FILTER.
    send                       Send encrypted secrets to a user via file or Slack.
    serializers                List available serializers.
    server                     Server commands.
        init                   Initialize a server vault
    setenv                     Set global environment variables from secrets matching FILTER.
    slack                      Slack-based secret exchange transport.
        doctor                 Preflight health check for the Slack exchange transport.
        link                   Bind a local user to a Slack handle after fingerprint confirmation.
        login                  OAuth login to Slack and pick an exchange channel.
        logout                 Wipe all Slack configuration from the vault.
        status                 Show Slack login / channel / last-seen state.
    upgrade                    Upgrade the database to the latest version
    users                      List the users in the vault
    whoami                     Display the current user and their role in the vault.
```

To get information on any command add the `-h` flag, e.g.:

```bash
> seeqret export -h
Usage: seeqret export [OPTIONS]

  Export the vault TO a user (use `seeqret load` to import)

  Example:

  seeqret export --to u1 --to u2 --f :app1::FOO* --f :app1::BAR* --s command

  This will export all secrets starting with FOO or BAR from app1 to users u1
  and u2.

Options:
  --to TEXT              User(s) to export to (can be used multiple times) the
                         user(s) must exist in the vault.  [required]
  -f, --filter TEXT      A seeqret filter string (can be used multiple times)
  -s, --serializer TEXT  Name of serializer to use (`seeqret serializers` to
                         list).  [default: json-crypt]
  -o, --out TEXT         Output file (default: stdout).
  -w, --windows          Export to windows format.
  -l, --linux            Export to linux format.
  -h, --help             Show this message and exit.
```

## <a name='Server'></a>Server
TBD

```bash
seeqret server init
```

...


---
[^1]: Updating means manually changing the secret (both in the storage and the service it protects), e.g. when a password expires/is compromised/a devloper leaves/etc.

[^2]: Rotation is the process of periodically updating a secret. Ideally this
is an automatic process that e.g. changes both the secret storage and the
service it protects.

[^3]: This is a defense-in-depth measure (in case the sanitizer fails to remove the secret from any traceback/logs/etc.)

[^4]: Auditing means checking who has access to the secrets, which secrets were accessed, and when.
