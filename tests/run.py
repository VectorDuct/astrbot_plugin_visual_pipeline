"""Expose repository as an AstrBot plugin package for standard unittest discovery."""
import pathlib
import sys
import types
import unittest

root = pathlib.Path(__file__).resolve().parents[1]
package = types.ModuleType('plugin')
package.__path__ = [str(root)]
sys.modules['plugin'] = package
suite = unittest.defaultTestLoader.discover(str(root / 'tests'), pattern='test_*.py')
raise SystemExit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
