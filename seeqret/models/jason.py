"""
Helper module to send json encoded data from Python.
(the misspelling is intentional ;-)
"""
# pylint:disable=E0202
import collections
import datetime
import decimal
import json
# import re

# # Call JSON.parse() if dk.jason.parse() is not available
# # (the re.sub() call removes all spaces, which is currently safe).
# CLIENT_PARSE_FN = re.sub(r'\s+', "", """
#     function (val) {
#         return (dk && dk.jason && dk.jason.parse) ?
#             dk.jason.parse(val) : JSON.parse(val)
#     }
# """)


# Are we sending a simple value, i.e. values that don't need the double parse
# required when sending '@type:__' encoded values?
# Currently, this only checks the top level of the value.
def _is_simpleval(val):
    if isinstance(val, (decimal.Decimal, int)):
        return True
    if isinstance(val, str) and not val.startswith('@'):
        return True
    return False


class DkJSONEncoder(json.JSONEncoder):
    """Handle special cases, like Decimal...
    """

    def default(self, o):

        if isinstance(o, decimal.Decimal):
            return float(o)
        if hasattr(o, '__json__'):
            return o.__json__()
        # if isinstance(o, set):
        #     return list(o)
        if isinstance(o, datetime.datetime):
            return f'{o.isoformat()}'
        if isinstance(o, datetime.date):
            return f'{o.isoformat()}'
        # if isinstance(o, datetime.time):
        #     return dict(hour=o.hour,
        #                 minute=o.minute,
        #                 second=o.second,
        #                 microsecond=o.microsecond,
        #                 kind="TIME")

        if hasattr(o, '__dict__'):
            return {k: v
                    for k, v in o.__dict__.items()
                    if not k.startswith('_')}

        if isinstance(o, collections.abc.Mapping):
            return dict(o)

        if isinstance(o, bytes):  # pragma: no branch
            return o.decode('u8')

        if isinstance(o, collections.abc.Iterable):
            return list(o)

        return super().default(o)


def dumps(val, indent=4, sort_keys=True, cls=DkJSONEncoder):
    """Dump json value, using our special encoder class.
    """
    return json.dumps(val, indent=indent, sort_keys=sort_keys, cls=cls)


def dump2(val, **kw):
    """Dump using a compact dump format.
    """
    kw['indent'] = kw.get('indent', None)
    kw['cls'] = kw.get('cls', DkJSONEncoder)
    kw['separators'] = kw.get('separators', (',', ':'))
    return json.dumps(val, **kw)

#
# DATETIME_RE = re.compile(r'''
#     @datetime:
#         (?P<year>\d{4})
#         -(?P<mnth>\d\d?)
#         -(?P<day>\d\d?)
#         T(?P<hr>\d\d?)
#         :(?P<min>\d\d?)
#         :(?P<sec>\d\d?)
#         (?:\.(?P<ms>\d+)Z?)?
# ''', re.VERBOSE)
#
#


def _iso_to_date(s):
    try:
        return datetime.date.fromisoformat(s)
    except ValueError:
        return None


def _iso_to_datetime(s):
    try:
        return datetime.datetime.fromisoformat(s)
    except ValueError:
        return None


def obj_decoder(pairs):
    """Reverses values created by DkJSONEncoder.
    """

    # def _get_tag(value):
    #     """Return the tag part of val, if it exists.
    #        Ie. @datetime:2021-11-15T12:15:47.1234 returns @datetime:
    #     """
    #     if isinstance(value, str) and value.startswith('@'):
    #         try:
    #             value = str(value)
    #         except UnicodeEncodeError:  # pragma: nocover
    #             return None
    #         else:
    #             if ':' not in value:
    #                 return None
    #             tag, _val = value.split(':', 1)
    #             return tag + ':'
    #     else:
    #         return None

    res = {}
    for key, val in pairs:
        if isinstance(val, str):
            if dt := _iso_to_date(val):
                val = dt
            elif dt := _iso_to_datetime(val):
                val = dt

        res[key] = val
    return res


def loads(txt, **kw):
    """Load json data from txt.
    """
    if 'cls' not in kw:
        kw['object_pairs_hook'] = kw.get('object_pairs_hook', obj_decoder)
    if isinstance(txt, bytes):
        txt = txt.decode('u8')
    return json.loads(txt, **kw)


def json_eval(txt):
    """Un-serialize json value.
    """
    return loads(txt)


def jsonname(val):
    """Convert the string in val to a valid json field name.
    """
    return val.replace('.', '_')
