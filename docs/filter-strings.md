# Filter spec

Several commands take a _filter-spec_, which is a string with the following
format:

    <app-spec>:<env-spec>:<name-spec>

Each part uses glob syntax. Parts can be left out:

| Filter-spec      | Means            |
|------------------|------------------|
| `NAME`           | `*:*:NAME`       |
| `APP:ENV`        | `APP:ENV:*`      |
| `APP:ENV:NAME`   | `APP:ENV:NAME`   |

An empty part means `*`, i.e. `foo:*:bar` can be written as `foo::bar`.

Colon is not an allowed character in app/env/name values.

Commands that act on a single secret (`seeqret get`, and `seeqret.get()` in
Python, see [Python API](python-api.md)) fail when the filter-spec matches
more than one secret.

## Examples

### all values

    *:*:*

it could have been

    *

but windows will do expansion on solitary stars, so

    ::

and just

    :

will work.

### all values for a specific app

    my-app:*:*

or

    my-app:*

or

    my-app:

### all development values for a specific app

    my-app:dev:*

or

    my-app:dev:

### all names starting with PG

    *:*:PG*

or

    ::PG*

or

    PG*

### all names ending with `_ID`

    *_ID
