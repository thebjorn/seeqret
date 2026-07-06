"""PyInstaller entry point for the seeqret GUI.

   ``seeqret/gui/__main__.py`` uses relative imports, so PyInstaller
   needs a top-level script to analyze -- this is it. The
   pip-installed package uses the ``seeqret-gui`` gui_script entry
   point instead; this file exists only for the frozen build.
"""
import sys

from seeqret.gui.__main__ import main

if __name__ == '__main__':
    sys.exit(main())
