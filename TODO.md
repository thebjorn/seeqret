# TODO

- [x] Fix init directory
- [x] Storage: sqlite3
- [x] Add key pair for native user
- [x] Add pkey for foreign user
- [x] Add app:env(key:value) pair
- [x] Export app:env(key:value) pair to foreign user
- [x] import export file
---

- [x] pluggable storage backends
- [x] pluggable export/import formats
- [ ] backup
- [ ] multi-signature secrets (Shamir)
- [ ] pluggable backup backends

- [ ] rename admin to owner?
- [ ] rename users to keyring?

---

- [ ] server installation
- [ ] re-key database

- `ssh thebjorn@myserver.com "/srv/venv/dev310/bin/python -V"` looks promising
  requires `%userprofile%\.ssh\id_rsa` to be present, valid, and have the
  correct permissions.

---

- [ ] update documentation


# Design

- [x] `seeqret list --filter ...`
- [x] `seeqret export to --filter ...`
  - [x] Filters: `::key == *:*:key` (all keys matching key regardless of app:env),
  - [x] `myapp:dev:*` (all keys for myapp in dev)
  - [x] `myapp-*::` (all keys for myapp-sales, myapp-marketing, etc)
- [ ] `seeqret import ...` selectively
- [ ] `seeqret update --filter <filter> --set env=prod`
- [x] more convenient export/import
- [ ] is there a way to do ACLs

## public key distribution mechanism
- web of trust (discrete webs can be safely merged whenever two persons)
  in different webs achieve a direct trust relationship, correct? - emergent
  web of confidence?)

## Server vault features
- [ ] differentiated features based on user
  - [ ] asdf

## commands

### init
```bash
  seeqret init --user bp --email bp@norsktest.no
```
in another directory
```bash
  seeqret init --user tkbe --email bjorn@tkbe.org
```

### add user
**Note:** the url here is suspect (no proof of ownership).

```bash
  seeqret add user --url https://raw.githubusercontent.com/tkbeorg/tkbe/refs/heads/main/public.key --username tkbe --email bjorn@tkbe.org
  seeqret add user --username bp --email bp@norsktest.no --url https://gitlab.com/thebjorn/public/-/raw/main/public.key?ref_type=heads
```

### add key
```bash
  seeqret add key SEECRET 42
```

```bash
@echo off
echo foo ^

this is ^

a multiline ^

echo > out.txt
@echo on

```
