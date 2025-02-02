
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


---
**footnotes**

[^1]: Updating means manually changing the secret (both in the storage and the service it protects), e.g. when a password expires/is compromised/a devloper leaves/etc.

[^2]: Rotation is the process of periodically updating a secret. Ideally this
is an automatic process that e.g. changes both the secret storage and the
service it protects.

[^3]: This is a defense-in-depth measure (in case the sanitizer fails to remove the secret from any traceback/logs/etc.)

[^4]: Auditing means checking who has access to the secrets, which secrets were accessed, and when.
