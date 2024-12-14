

import os
import tempfile
from seeqret import seeqret_init


def test_init():
    with tempfile.TemporaryDirectory() as temp_dir:
        seeqret_init.secrets_init(temp_dir)
        # seeqret_init.secrets_init()
        assert os.path.exists(os.path.join(temp_dir, '.seeqret'))
        print(temp_dir)
