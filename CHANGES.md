# CHANGES

API changes to seeqret. Use this to synchronize with
[jseeqret](https://github.com/thebjorn/jseeqret).

## 0.3.9

- `seeqret list` now accepts an optional positional filterspec argument.
  `seeqret list yerbu:prod:` is equivalent to `seeqret list -f yerbu:prod:`.
  The `-f`/`--filter` flag is still supported for backward compatibility.
  When both are provided, `-f` takes precedence.
