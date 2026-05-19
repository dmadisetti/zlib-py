"""Adler-32 tests vendored from CPython's Lib/test/test_zlib.py.

Source: https://github.com/python/cpython/blob/5775aa8e295102156de14fd1ba284722c6ede95a/Lib/test/test_zlib.py
Commit: 5775aa8e295102156de14fd1ba284722c6ede95a (3.16-alpha)

Only adler32-specific methods are included here. Mixed adler32/crc32 cases
(`test_penguins`, `test_crc32_adler32_unsigned`) are vendored in
`tests/test_crc32.py` once `crc32` is implemented.

The bodies are reproduced verbatim, with `zlib` rebound to `zlib_py` at
import time so the assertions exercise our implementation rather than the
stdlib.
"""

import unittest

import zlib_py as zlib  # so vendored bodies run against our module unmodified


class ChecksumTestCase(unittest.TestCase):
    # Lines 85-87 of Lib/test/test_zlib.py @ 5775aa8e
    def test_adler32start(self):
        self.assertEqual(zlib.adler32(b""), zlib.adler32(b"", 1))
        self.assertTrue(zlib.adler32(b"abc", 0xffffffff))

    # Lines 89-93 of Lib/test/test_zlib.py @ 5775aa8e
    def test_adler32empty(self):
        self.assertEqual(zlib.adler32(b"", 0), 0)
        self.assertEqual(zlib.adler32(b"", 1), 1)
        self.assertEqual(zlib.adler32(b"", 432), 432)


if __name__ == "__main__":
    unittest.main()
