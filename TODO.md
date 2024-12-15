# TODO

- [x] Fix init directory
- [x] Storage: sqlite3
- [x] Add key pair for native user
- [x] Add pkey for foreign user
- [x] Add app:env(key:value) pair
- [x] Export app:env(key:value) pair to foreign user
- [x] import export file

# Design

- [ ] `seeqret list --filter ...`
- [ ] `seeqret export to --filter ...`
  - [ ] Filters: `::key == *:*:key` (all keys matching key regardless of app:env), 
  - [ ] `myapp:dev:*` (all keys for myapp in dev)
  - [ ] `myapp-*::` (all keys for myapp-sales, myapp-marketing, etc)
- [ ] `seeqret import ...` selectively
- [ ] `seeqret update --filter <filter> --set env=prod`
- [ ] more convenient export/import


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