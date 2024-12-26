from seeqret.seeqret_add import *
import pytest


def test_fetch_pubkey_from_url():
    pubkey = fetch_pubkey_from_url('https://raw.githubusercontent.com/tkbeorg/tkbe/refs/heads/main/public.key')
    assert pubkey == 'ilxSnX9+NrwmeIzOFtWrl0lPPkxTEATmC39BILX6rWk=\n'

    with pytest.raises(RuntimeError):
        fetch_pubkey_from_url('https://raw.githubusercontent.com/tkbeorg/tkbe/refs/heads/main/xxx')
