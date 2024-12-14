# TODO

- [x] Fix init directory
- [x] Storage: sqlite3
- [x] Add key pair for native user
- [ ] Add pkey for foreign user
- [ ] Add app:env(key:value) pair
- [ ] Export app:env(key:value) pair to foreign user

## commands

### init
```bash
  seeqret init --email bp@norsktest.no
```

### add user
```bash
  seeqret add user --url https://raw.githubusercontent.com/tkbeorg/tkbe/refs/heads/main/public.key --username tkbe --email bjorn@tkbe.org
```

### add key
```bash
  seeqret add key SEECRET 42
```
