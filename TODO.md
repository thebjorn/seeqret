# TODO

- [x] Fix init directory
- [x] Storage: sqlite3
- [x] Add key pair for native user
- [x] Add pkey for foreign user
- [x] Add app:env(key:value) pair
- [x] Export app:env(key:value) pair to foreign user
- [x] import export file

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
```

### add key
```bash
  seeqret add key SEECRET 42
```
