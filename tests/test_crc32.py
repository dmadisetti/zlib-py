"""CRC-32 tests vendored from CPython's Lib/test/test_zlib.py.

Source: https://github.com/python/cpython/blob/5775aa8e295102156de14fd1ba284722c6ede95a/Lib/test/test_zlib.py
Commit: 5775aa8e295102156de14fd1ba284722c6ede95a (3.16-alpha)

`test_penguins` and `test_crc32_adler32_unsigned` exercise both adler32
and crc32 in the same method; they live here (the later commit) so
both functions are implemented by the time the assertions run.

The bodies are reproduced verbatim, with `zlib` rebound to `zlib_py` at
import time so the assertions exercise our implementation rather than
the stdlib.
"""

import binascii
import unittest

import zlib_py as zlib  # so vendored bodies run against our module unmodified


class ChecksumTestCase(unittest.TestCase):
    # Lines 76-78 of Lib/test/test_zlib.py @ 5775aa8e
    def test_crc32start(self):
        self.assertEqual(zlib.crc32(b""), zlib.crc32(b"", 0))
        self.assertTrue(zlib.crc32(b"abc", 0xffffffff))

    # Lines 80-83 of Lib/test/test_zlib.py @ 5775aa8e
    def test_crc32empty(self):
        self.assertEqual(zlib.crc32(b"", 0), 0)
        self.assertEqual(zlib.crc32(b"", 1), 1)
        self.assertEqual(zlib.crc32(b"", 432), 432)

    # Lines 95-101 of Lib/test/test_zlib.py @ 5775aa8e
    def test_penguins(self):
        self.assertEqual(zlib.crc32(b"penguin", 0), 0x0e5c1a120)
        self.assertEqual(zlib.crc32(b"penguin", 1), 0x43b6aa94)
        self.assertEqual(zlib.adler32(b"penguin", 0), 0x0bcf02f6)
        self.assertEqual(zlib.adler32(b"penguin", 1), 0x0bd602f7)

        self.assertEqual(zlib.crc32(b"penguin"), zlib.crc32(b"penguin", 0))
        self.assertEqual(zlib.adler32(b"penguin"),zlib.adler32(b"penguin",1))

    # Lines 103-108 of Lib/test/test_zlib.py @ 5775aa8e
    def test_crc32_adler32_unsigned(self):
        foo = b'abcdefghijklmnop'
        # explicitly test signed behavior
        self.assertEqual(zlib.crc32(foo), 2486878355)
        self.assertEqual(zlib.crc32(b'spam'), 1138425661)
        self.assertEqual(zlib.adler32(foo+foo), 3573550353)
        self.assertEqual(zlib.adler32(b'spam'), 72286642)

    # Lines 110-117 of Lib/test/test_zlib.py @ 5775aa8e
    def test_same_as_binascii_crc32(self):
        foo = b'abcdefghijklmnop'
        crc = 2486878355
        self.assertEqual(binascii.crc32(foo), crc)
        self.assertEqual(zlib.crc32(foo), crc)
        self.assertEqual(binascii.crc32(b'spam'), zlib.crc32(b'spam'))


if __name__ == "__main__":
    unittest.main()
