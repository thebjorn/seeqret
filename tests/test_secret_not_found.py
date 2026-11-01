import pytest
from click.testing import CliRunner

import seeqret
from seeqret.main import init
from seeqret.cli_group_add import key
from seeqret.run_utils import seeqret_dir
from seeqret.storage.get_secret import parse_secret_ref
from seeqret.storage.storage import SecretNotFound
from tests.clirunner_utils import print_result


def test_message_names_secret_and_location():
    err = SecretNotFound('CRON_SECRET', 'yerbu', 'prod', '/vault/seeqrets.db')
    msg = str(err)
    assert 'yerbu:prod:CRON_SECRET' in msg
    assert '/vault/seeqrets.db' in msg
    assert 'seeqret list "*:*:CRON_SECRET"' in msg


def test_is_key_error_and_index_error():
    err = SecretNotFound('X')
    assert isinstance(err, KeyError)
    assert isinstance(err, IndexError)   # backward compatibility


@pytest.mark.parametrize('ref, app, env, expected', [
    ('CRON_SECRET', '*', '*', ('CRON_SECRET', '*', '*')),
    ('CRON_SECRET', 'yerbu', 'prod', ('CRON_SECRET', 'yerbu', 'prod')),
    ('yerbu:prod:CRON_SECRET', '*', '*', ('CRON_SECRET', 'yerbu', 'prod')),
    ('::CRON_SECRET', '*', '*', ('CRON_SECRET', '*', '*')),
    (':prod:CRON_SECRET', '*', '*', ('CRON_SECRET', '*', 'prod')),
])
def test_parse_secret_ref(ref, app, env, expected):
    assert parse_secret_ref(ref, app, env) == expected


@pytest.mark.parametrize('ref, app, env', [
    ('yerbu:prod', '*', '*'),               # no key part
    ('yerbu:prod:', '*', '*'),              # empty key part
    ('a:b:c:d', '*', '*'),                  # too many parts
    ('yerbu:prod:CRON_SECRET', 'yerbu', '*'),   # app given twice
    ('yerbu:prod:CRON_SECRET', '*', 'prod'),    # env given twice
])
def test_parse_secret_ref_rejects(ref, app, env):
    with pytest.raises(ValueError):
        parse_secret_ref(ref, app, env)


def test_get_accepts_filter_string_and_raises_secret_not_found():
    runner = CliRunner(env=dict(TESTING='TRUE'))
    with runner.isolated_filesystem():
        result = runner.invoke(init, [
            '.',
            '--user=test',
            '--email=test@example.com',
        ])
        if result.exit_code != 0: print_result(result)
        assert result.exit_code == 0

        result = runner.invoke(key, [
            'CRON_SECRET', 'hush',
            '--app=yerbu',
            '--env=prod',
        ])
        if result.exit_code != 0: print_result(result)
        assert result.exit_code == 0

        with seeqret_dir():
            assert seeqret.get('yerbu:prod:CRON_SECRET') == 'hush'
            assert seeqret.get('CRON_SECRET', 'yerbu', 'prod') == 'hush'
            assert seeqret.get('::CRON_SECRET') == 'hush'

            with pytest.raises(seeqret.SecretNotFound) as excinfo:
                seeqret.get('yerbu:dev:CRON_SECRET')
            assert 'yerbu:dev:CRON_SECRET' in str(excinfo.value)
            assert 'seeqrets.db' in str(excinfo.value)


def test_get_raises_when_several_secrets_match():
    runner = CliRunner(env=dict(TESTING='TRUE'))
    with runner.isolated_filesystem():
        result = runner.invoke(init, [
            '.',
            '--user=test',
            '--email=test@example.com',
        ])
        if result.exit_code != 0: print_result(result)
        assert result.exit_code == 0

        for env, value in [('prod', 'prod-value'), ('dev', 'dev-value')]:
            result = runner.invoke(key, [
                'CRON_SECRET', value,
                '--app=yerbu',
                f'--env={env}',
            ])
            if result.exit_code != 0: print_result(result)
            assert result.exit_code == 0

        with seeqret_dir():
            assert seeqret.get('yerbu:dev:CRON_SECRET') == 'dev-value'

            with pytest.raises(seeqret.AmbiguousSecret) as excinfo:
                seeqret.get('::CRON_SECRET')
            err = excinfo.value
            assert isinstance(err, LookupError)
            assert err.matches == [
                'yerbu:dev:CRON_SECRET',
                'yerbu:prod:CRON_SECRET',
            ]

            msg = str(err)
            assert '2 secrets match *:*:CRON_SECRET' in msg
            # the message must never leak secret values
            assert 'prod-value' not in msg
            assert 'dev-value' not in msg
            assert 'prod-value' not in repr(err)
