# Filter spec

Several commands take a _filter-spec_, which is a string with the following
format:

    <app-spec>:<env-spec>:<name-spec>

Each part (between colons) is required and uses glob syntax.

Colon is not an allowed character in app/env/name values.

`*` values can usually be omitted, i.e. `foo:*:bar` can be written as
`foo::bar`.

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
