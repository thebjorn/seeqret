# Python API

```python
import seeqret

cn = psycopg.connect(..., password=seeqret.get('myapp:prod:DB_PASSWORD'))
```

`seeqret.get()` reads one secret from the local vault, decrypts it and
returns its value. It is fast (thousands of lookups per second), so there is
no need to cache the result.

## Fetch secrets at the last possible moment

Call `seeqret.get()` where the secret is used, not in a settings module.
A secret held in a module-level variable can end up in tracebacks, debug
pages and logs:

```python
DB_PASSWORD = seeqret.get('myapp:prod:DB_PASSWORD')       # BAD

cn = mydb.connect(..., password=seeqret.get('myapp:prod:DB_PASSWORD'))  # GOOD
```

## Naming a secret

A secret is identified by `app`, `env` and `key`. You can name it the same
way as on the command line (`seeqret get myapp:prod:DB_PASSWORD`), or pass
the parts separately:

```python
seeqret.get('myapp:prod:DB_PASSWORD')
seeqret.get('DB_PASSWORD', app='myapp', env='prod')    # same secret
```

| Call                                    | Looks up                 |
|-----------------------------------------|--------------------------|
| `seeqret.get('myapp:prod:DB_PASSWORD')` | `myapp:prod:DB_PASSWORD` |
| `seeqret.get(':prod:DB_PASSWORD')`      | `*:prod:DB_PASSWORD`     |
| `seeqret.get('::DB_PASSWORD')`          | `*:*:DB_PASSWORD`        |
| `seeqret.get('DB_PASSWORD')`            | `*:*:DB_PASSWORD`        |

Empty parts mean `*`, as in [filter strings](filter-strings.md). Use either
the `app:env:key` form or the `app=`/`env=` arguments, not both.

The reference must match exactly one secret. `*` in a reference is a
wildcard, so a reference like `'::DB_PASSWORD'` fails if the key exists in
more than one app or environment.

## Return value

The decrypted value, converted according to the secret's type: `str`
secrets are returned as `str`, `int` secrets as `int`.

## Errors

| Exception                 | Raised when                                                    |
|---------------------------|----------------------------------------------------------------|
| `seeqret.SecretNotFound`  | no secret matches                                              |
| `seeqret.AmbiguousSecret` | more than one secret matches                                   |
| `ValueError`              | the reference is malformed or conflicts with `app=`/`env=`     |

The messages say what was looked up and how to find the secret, e.g.:

```
seeqret.storage.storage.SecretNotFound: No secret yerbu:dev:CRON_SECRET in vault C:\srv\seeqret\seeqrets.db.
See where 'CRON_SECRET' exists with: seeqret list "*:*:CRON_SECRET"
```

```
seeqret.storage.storage.AmbiguousSecret: 2 secrets match *:*:CRON_SECRET:
    yerbu:dev:CRON_SECRET
    yerbu:prod:CRON_SECRET
Name the app and env, e.g. seeqret.get('yerbu:dev:CRON_SECRET').
```

Neither message contains secret values.

`SecretNotFound` is a `KeyError` (and an `IndexError`, which older versions
raised). `AmbiguousSecret` is a `LookupError`, and its `matches` attribute
lists the matching `app:env:key` names. To handle both:

```python
try:
    token = seeqret.get('myapp:prod:API_TOKEN')
except LookupError as err:
    sys.exit(str(err))
```

## Which vault is used

On Windows, and whenever the `SEEQRET` environment variable is set, the vault
is the directory `SEEQRET` points to (`seeqret init` sets it on Windows).
Otherwise it is `/srv/.seeqret`.
