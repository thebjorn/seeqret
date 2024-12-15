import os
import tempfile
from pathlib import Path
from seeqret import seeqret_init


def test_init():
    with tempfile.TemporaryDirectory() as temp_dir:
        seeqret_init.secrets_init(Path(temp_dir), 'test', 'test@example.com', None)
        # seeqret_init.secrets_init()
        assert os.path.exists(os.path.join(temp_dir, 'seeqret'))
        assert os.path.exists(os.path.join(temp_dir, 'seeqret', 'private.key'))
        assert os.path.exists(os.path.join(temp_dir, 'seeqret', 'public.key'))
        assert os.path.exists(os.path.join(temp_dir, 'seeqret', 'seeqret.key'))
        assert os.path.exists(os.path.join(temp_dir, 'seeqret', 'seeqrets.db'))
