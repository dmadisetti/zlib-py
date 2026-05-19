"""Misc tests vendored from CPython's Lib/test/test_zlib.py.

Source: https://github.com/python/cpython/blob/5775aa8e295102156de14fd1ba284722c6ede95a/Lib/test/test_zlib.py
Commit: 5775aa8e295102156de14fd1ba284722c6ede95a (3.16-alpha)

Groups `VersionTestCase`, `ExceptionTestCase`, and `TestModule` into one
file so the small classes don't sprawl into separate modules. Bodies are
reproduced verbatim apart from rebinding `zlib` → `zlib_py`.
"""

import unittest

import zlib_py as zlib  # so vendored bodies run against our module unmodified


class VersionTestCase(unittest.TestCase):

    # Lines 68-74 of Lib/test/test_zlib.py @ 5775aa8e
    def test_library_version(self):
        # Test that the major version of the actual library in use matches the
        # major version that we were compiled against. We can't guarantee that
        # the minor versions will match (even on the machine on which the module
        # was compiled), and the API is stable between minor versions, so
        # testing only the major versions avoids spurious failures.
        self.assertEqual(zlib.ZLIB_RUNTIME_VERSION[0], zlib.ZLIB_VERSION[0])


class ExceptionTestCase(unittest.TestCase):
    # make sure we generate some expected errors

    # Lines 242-246 of Lib/test/test_zlib.py @ 5775aa8e
    def test_badlevel(self):
        # specifying compression level out of range causes an error
        # (but -1 is Z_DEFAULT_COMPRESSION and apparently the zlib
        # accepts 0 too)
        self.assertRaises(zlib.error, zlib.compress, b'ERROR', 10)

    # Lines 248-257 of Lib/test/test_zlib.py @ 5775aa8e
    def test_badargs(self):
        self.assertRaises(TypeError, zlib.adler32)
        self.assertRaises(TypeError, zlib.crc32)
        self.assertRaises(TypeError, zlib.compress)
        self.assertRaises(TypeError, zlib.decompress)
        for arg in (42, None, '', 'abc', (), []):
            self.assertRaises(TypeError, zlib.adler32, arg)
            self.assertRaises(TypeError, zlib.crc32, arg)
            self.assertRaises(TypeError, zlib.compress, arg)
            self.assertRaises(TypeError, zlib.decompress, arg)

    # Lines 259-264 of Lib/test/test_zlib.py @ 5775aa8e
    def test_badcompressobj(self):
        # verify failure on building compress object with bad params
        self.assertRaises(ValueError, zlib.compressobj, 1, zlib.DEFLATED, 0)
        # specifying total bits too large causes an error
        self.assertRaises(ValueError,
                zlib.compressobj, 1, zlib.DEFLATED, zlib.MAX_WBITS + 1)

    # Lines 266-268 of Lib/test/test_zlib.py @ 5775aa8e
    def test_baddecompressobj(self):
        # verify failure on building decompress object with bad params
        self.assertRaises(ValueError, zlib.decompressobj, -1)

    # Lines 270-273 of Lib/test/test_zlib.py @ 5775aa8e
    def test_decompressobj_badflush(self):
        # verify failure on calling decompressobj.flush with bad params
        self.assertRaises(ValueError, zlib.decompressobj().flush, 0)
        self.assertRaises(ValueError, zlib.decompressobj().flush, -1)


class TestModule(unittest.TestCase):
    # Lines 1226-1232 of Lib/test/test_zlib.py @ 5775aa8e
    def test_deprecated__version__(self):
        with self.assertWarnsRegex(
                DeprecationWarning,
                "'__version__' is deprecated and slated for removal in Python 3.20",
        ) as cm:
            getattr(zlib, "__version__")
        self.assertEqual(cm.filename, __file__)


if __name__ == "__main__":
    unittest.main()
