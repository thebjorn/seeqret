# Safely transferring code secrets
(very much a work in progress)

![cicd](https://github.com/thebjorn/seeqret/actions/workflows/ci.yml/badge.svg)
[![codecov](https://codecov.io/gh/thebjorn/seeqret/graph/badge.svg?token=5PQOZLTSYD)](https://codecov.io/gh/thebjorn/seeqret)
[![pypi](https://img.shields.io/pypi/v/seeqret?label=pypi%20seeqret)](https://pypi.org/project/seeqret/)
[![downloads](https://pepy.tech/badge/seeqret)](https://pepy.tech/project/seeqret)
<a href="https://github.com/thebjorn/seeqret"><img src="docs/github-mark/github-mark.png" width="25" height="25"></a>

![codecov](https://codecov.io/gh/thebjorn/seeqret/graphs/sunburst.svg?token=5PQOZLTSYD)

<img src="docs/seeqret-logo-256.png" width=100 style="float:right">

# Seeqret: Safely transferring code secrets
(very much a work in progress)


![Seeqret Logo](docs/seeqret-logo-256.png)

<!-- @import "[TOC]" {cmd="toc" depthFrom=1 depthTo=6 orderedList=false} -->

<!-- code_chunk_output -->

- [Safely transferring code secrets](#safely-transferring-code-secrets)
  - [Introduction](#introduction)
    - [Prior art...](#prior-art)
  - [Assumptions](#assumptions)
  - [Minimum Requirements](#minimum-requirements)
- [Use cases](#use-cases)
- [Code](#code)

<!-- /code_chunk_output -->



## Introduction

How do you communicate the set of secrets (passwords, API keys, etc.) that your code needs to run? You can't just write them in the code, because that would expose them to anyone who can read the code. You can't just send them in an email, because that would expose them to anyone who can read your email. You can't just write them on a sticky note, because that would expose them to anyone who can read your sticky note.

### Prior art...

There are many ways to store and use secrets, e.g.:

- **Environment variables**: It is popular, in e.g. kubernetes and javascript, to read secrets from environment variables. For development these are stored in .env files that are not checked into git/svn. These files contain the secrets in plain-text. Transferring secrets to a new server/devloper is a manual process where you create a new file and somehow get access to the secrets.

- **Key vaults**: E.g. Secureden or HashiCorp Vault (can be self hosted). These are usually expensive or complex to set up - or both. Key vaults usually have an API that you can use to get the secrets (setting this up is also expensive/complex/both).

- **Secret management services**: These are hosted key vaults, e.g. AWS Secrets Manager, Google Secret manager, Azure Key Vault, or hosted HashiCorp Vault. There is always an associated api to read the secrets. This can incur significant costs for large numbers of secrets and/or high usage.

- **Encrypted files**: This is usually a key/value file (.json/.yaml), where only the values are encrypted (e.g. [SOPS](https://github.com/getsops/sops). Every developer must have the same key to be able to use the file, but the file can be stored in git/svn.

## Assumptions
You can make the following assumptions:

- https is secure
- the encryption algorithms are secure
- encrypted directories (Windows) are secure
  ```bat
  attrib +I %1
  icacls %1 /grant %USERDOMAIN%\%USERNAME%:(F) /T
  icacls %1 /inheritance:r
  cipher /e %1
  ```
- [encrypted private directories](https://help.ubuntu.com/community/EncryptedPrivateDirectory) (Ubuntu) are secure.
- `0600` (read/write by owner only) directories (linux) are safe provided the user is not compromised.

## Minimum Requirements
1. different users/systems should have access to different subsets of the secrets.
2. the secrets should not exist in plain-text when they are not used (e.g. a
   database password is only _used_ when logging into the database - it shouldn't exist in memory outside of this process[^3]).
3. a subset of secrets needs to be **shared with new developers** in a secure way.
4. there should be a command line utility (`secrets`) to
   - `secrets set <key> <value>`: set a secret
   - `secrets get <key>`: get a secret
   - `secrets export <user> <keys..>` export a subset of the secrets for transmission (e.g. by email) to a new developer
   - `secrets import <keys..>` import keys received by e.g. email
5. and a library/API to
   - `secrets.get(key)`: get a secret (this should be a fast O(1) operation)
5. the secrets should be easy to update[^1].
6. it should be possible to backup the secrets.
7. _(bonus)_: the secrets should be easy to rotate[^2].
8. _(bonus)_: the secrets should be auditable[^4].

# Use cases

1. **Starting from scratch:** How do you set up the secrets system?
2. **Inviting users:** How do you invite users and how do you communicate the secrets to them?
3. **Adding a secret:** How do you communicate a new secret to the users?
4. **Updating a secret:** How do you communicate an update to a secret?
5. **New user:** How does a new user get access to the secrets?
6. **Backup:** How do you backup the secrets and what is needed to restore the backup?
7. **Developer leaves:** How do you revoke access to the secrets for a developer that leaves?


# Code
The code in the `filecrypt.py` file is from [Asymetric Encryption](https://www.youtube.com/watch?v=bd5nsMscPo0) which is well worth watching...

The code in `pgp_filecrypt.py` contains the code needed to do pgp encryption/decryption (here you need to set the trust level when importing keys to the people you want to send encrypted messages to).


[^1]: Updating means manually changing the secret (both in the storage and the service it protects), e.g. when a password expires/is compromised/a devloper leaves/etc.

[^2]: Rotation is the process of periodically updating a secret. Ideally this
is an automatic process that e.g. changes both the secret storage and the
service it protects.

[^3]: This is a defense-in-depth measure (in case the sanitizer fails to remove the secret from any traceback/logs/etc.)

[^4]: Auditing means checking who has access to the secrets, which secrets were accessed, and when.
