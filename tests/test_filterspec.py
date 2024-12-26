from seeqret.filterspec import FilterSpec


def test_filterspec():
    items = [
        ('*', '*', 'PG_PASSWORD'),
        ('myapp', '*', 'PG_PASSWORD'),
        ('myapp', 'dev', 'PG_PASSWORD'),
    ]


    f = FilterSpec('*')
    assert str(f) == '*:*:*'
    assert list(f.filter(items)) == items

    f = FilterSpec('PG*')
    assert str(f) == "*:*:PG*"
    assert list(f.filter(items)) == items

    f = FilterSpec('myapp:*')
    assert str(f) == 'myapp:*:*'
    assert list(f.filter(items)) == items[1:]

    f = FilterSpec('myapp:dev:*')
    assert str(f) == 'myapp:dev:*'
    assert list(f.filter(items)) == [items[2]]
