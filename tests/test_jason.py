import collections
import json
import sys

import pytest
import datetime
import decimal

from seeqret.models import jason


def roundtrip(v):
    "Convenience function to thest the roundtrip (dump/eval)."
    return jason.json_eval(jason.dumps(v)) == v


def test_jason_eval():
    "Test the jason_eval function using the roundtrip convenience function."
    assert roundtrip([])
    assert roundtrip(['hello world'])
    assert roundtrip(['hello world'.split()])
    assert roundtrip({})


def test_dumps():
    "Test the dumps function."
    dt = datetime.datetime(2012, 4, 2, 6, 12)
    assert jason.dumps(dt, indent=None) == '"2012-04-02T06:12:00"'
    assert jason.dumps(decimal.Decimal('3.14159263')) == repr(float('3.14159263'))
    assert jason.dumps({}.keys()) == '[]'
    assert jason.dumps({}.values()) == '[]'
    assert jason.dumps(range(0)) == '[]'
    assert jason.dumps(u'hello'.encode('u8')) == '"hello"'


def test_generator():
    assert jason.dumps((i for i in range(0))) == '[]'


def test_dictviews():
    a42 = dict(a=42)
    assert jason.json_eval(jason.dumps(a42.keys())) == ['a']
    assert jason.json_eval(jason.dumps(a42.values())) == [42]


def test_class_dumps():
    """Test the dump of the jason value of a class by using
       the __jason__ method.
    """

    class C:
        def __json__(self):
            return 42

    assert jason.dumps(C()) == '42'

    class D(object):
        def __init__(self):
            self.a = 42

    assert jason.json_eval(jason.dumps(D())) == {"a": 42}


def test_set_dumps():
    assert jason.json_eval(jason.dumps(1)) == 1
    assert jason.json_eval(jason.dumps(set())) == []
    assert jason.json_eval(jason.dumps({1, 2})) == [1, 2]
    assert jason.dumps(datetime.date(2019, 3, 15)) == '"2019-03-15"'

    class Foo(object):
        __slots__ = ['a', 'b']

    with pytest.raises(TypeError):
        jason.dumps(Foo())  # not JSON serializable


def test_mapping():
    class Bar(collections.abc.Mapping):
        __slots__ = ['a']

        def __getitem__(self, item):  # pragma: nocover
            pass

        def __iter__(self):
            return iter([])

        def __len__(self):  # pragma: nocover
            return 0

    assert isinstance(Bar(), collections.abc.Mapping)
    assert jason.dumps(Bar()) == "{}"


def test_loads():
    val = '{"k":"1970-05-02T06:10:00"}'
    jval = jason.loads(val)
    assert jval['k'] == datetime.datetime(1970, 5, 2, 6, 10)

    val = '{"k":"1970-05-02"}'
    jval = jason.loads(val)
    assert jval['k'] == datetime.date(1970, 5, 2)

    val = '{"k":"1970-05-02"}'
    jval = jason.loads(val)
    assert isinstance(jval['k'], datetime.date)

    val = '{"k":"@date1970-05-02"}'
    jval = jason.loads(val)
    assert not isinstance(jval['k'], datetime.date)

    val = '{"k":42}'
    jval = jason.loads(val)
    assert jval['k'] == 42

    val = b'{"k":42}'
    jval = jason.loads(val)
    assert jval['k'] == 42

    import json
    val = b'{"k":42}'
    jval = jason.loads(val, cls=json.JSONDecoder)
    assert jval['k'] == 42


def test_jsonname():
    assert jason.jsonname("hello.world") == "hello_world"
