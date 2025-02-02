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


        attrib +I %1
        icacls %1 /grant %USERDOMAIN%\%USERNAME%:(F) /T
        icacls %1 /inheritance:r
        cipher /e %1


- [encrypted private directories](https://help.ubuntu.com/community/EncryptedPrivateDirectory) (Ubuntu) are secure.
- `0600` (read/write by owner only) directories (linux) are safe provided the user is not compromised.
