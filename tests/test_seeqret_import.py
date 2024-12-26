"""
Test that all modules are importable.
"""

import seeqret
import seeqret.db_utils
import seeqret.fileutils
import seeqret.main
import seeqret.run_utils
import seeqret.seeqret_add
import seeqret.seeqret_init
import seeqret.seeqret_transfer
import seeqret.seeqrypt
import seeqret.seeqrypt.aes_fernet
import seeqret.seeqrypt.nacl_backend
import seeqret.seeqrypt.utils


def test_import_seeqret():
    """Test that all modules are importable.
    """
    
    assert seeqret
    assert seeqret.db_utils
    assert seeqret.fileutils
    assert seeqret.main
    assert seeqret.run_utils
    assert seeqret.seeqret_add
    assert seeqret.seeqret_init
    assert seeqret.seeqret_transfer
    assert seeqret.seeqrypt
    assert seeqret.seeqrypt.aes_fernet
    assert seeqret.seeqrypt.nacl_backend
    assert seeqret.seeqrypt.utils
