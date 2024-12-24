"""
Test that all modules are importable.
"""

import seeqret
import seeqret.main
import seeqret.seeqret_add
import seeqret.seeqret_init
import seeqret.seeqrypt
import seeqret.seeqrypt.aes_fernet
import seeqret.seeqrypt.nacl_backend
import seeqret.seeqrypt.utils
import seeqret.utils


def test_import_seeqret():
    """Test that all modules are importable.
    """

    assert seeqret
    assert seeqret.main
    assert seeqret.seeqret_add
    assert seeqret.seeqret_init
    assert seeqret.seeqrypt
    assert seeqret.seeqrypt.aes_fernet
    assert seeqret.seeqrypt.nacl_backend
    assert seeqret.seeqrypt.utils
    assert seeqret.utils
