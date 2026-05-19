"""Bigmem tests vendored from CPython's Lib/test/test_zlib.py.

Source: https://github.com/python/cpython/blob/5775aa8e295102156de14fd1ba284722c6ede95a/Lib/test/test_zlib.py
Commit: 5775aa8e295102156de14fd1ba284722c6ede95a (3.16-alpha)

Every test here is decorated with CPython's ``@bigmemtest`` (and some
also ``@unittest.skipUnless(sys.maxsize > 2**32, ...)``). Both depend on
CPython's ``test.support`` harness, which we don't import. Rather than
re-implement the harness, each method is wrapped with ``@unittest.skip``
and the body is preserved verbatim — so a future change to pull in
``test.support`` reactivates them with zero edits.

The CPython class layout is preserved (one Python class per CPython
class) so the file-line-commit attribution stays meaningful.
"""

import unittest

import zlib_py as zlib  # so vendored bodies run against our module unmodified

from tests.test_compress import HAMLET_SCENE  # vendored block, reused


_SKIP = "requires CPython test.support.bigmemtest harness"


# Lines 231-238 of Lib/test/test_zlib.py @ 5775aa8e
class ChecksumBigBufferTestCase(unittest.TestCase):

    # @bigmemtest(size=_4G + 4, memuse=1, dry_run=False)
    @unittest.skip(_SKIP)
    def test_big_buffer(self, size=None):
        data = b"nyan" * ((1 << 30) + 1)  # _1G + 1
        self.assertEqual(zlib.crc32(data), 1044521549)
        self.assertEqual(zlib.adler32(data), 2256789997)


# Lines 291-385 of Lib/test/test_zlib.py @ 5775aa8e (CompressTestCase bigmem methods)
class CompressTestCaseBigMem(unittest.TestCase):

    # Lines 357-360 of Lib/test/test_zlib.py @ 5775aa8e
    # @bigmemtest(size=_1G + 1024 * 1024, memuse=3)
    @unittest.skip(_SKIP)
    def test_big_compress_buffer(self, size=None):
        compress = lambda s: zlib.compress(s, 1)
        # NB: would normally call self.check_big_compress_buffer(size, compress)
        # — the helper lives on BaseCompressTestCase in CPython. Skipped here.

    # Lines 362-364 of Lib/test/test_zlib.py @ 5775aa8e
    # @bigmemtest(size=_1G + 1024 * 1024, memuse=2)
    @unittest.skip(_SKIP)
    def test_big_decompress_buffer(self, size=None):
        # would call: self.check_big_decompress_buffer(size, zlib.decompress)
        pass

    # Lines 366-371 of Lib/test/test_zlib.py @ 5775aa8e
    # @bigmemtest(size=_4G, memuse=1)
    @unittest.skip(_SKIP)
    def test_large_bufsize(self, size=None):
        # Test decompress(bufsize) parameter greater than the internal limit
        data = HAMLET_SCENE * 10
        compressed = zlib.compress(data, 1)
        self.assertEqual(zlib.decompress(compressed, 15, size), data)

    # Lines 379-385 of Lib/test/test_zlib.py @ 5775aa8e
    # @unittest.skipUnless(sys.maxsize > 2**32, 'requires 64bit platform')
    # @bigmemtest(size=_4G + 100, memuse=4)
    @unittest.skip(_SKIP)
    def test_64bit_compress(self, size=None):
        data = b'x' * size
        try:
            comp = zlib.compress(data, 0)
            self.assertEqual(zlib.decompress(comp), data)
        finally:
            comp = data = None


# Lines 389-921 of Lib/test/test_zlib.py @ 5775aa8e (CompressObjectTestCase bigmem methods)
class CompressObjectTestCaseBigMem(unittest.TestCase):

    # Lines 769-775 of Lib/test/test_zlib.py @ 5775aa8e
    # @bigmemtest(size=_4G + 100, memuse=1)
    @unittest.skip(_SKIP)
    def test_flush_large_length(self, size=None):
        # Test flush(length) parameter greater than internal limit UINT_MAX
        input = HAMLET_SCENE * 10
        data = zlib.compress(input, 1)
        dco = zlib.decompressobj()
        dco.decompress(data, 1)
        self.assertEqual(dco.flush(size), input[1:])

    # Lines 867-871 of Lib/test/test_zlib.py @ 5775aa8e
    # @bigmemtest(size=_1G + 1024 * 1024, memuse=3)
    @unittest.skip(_SKIP)
    def test_big_compress_buffer(self, size=None):
        c = zlib.compressobj(1)
        compress = lambda s: c.compress(s) + c.flush()
        # would call: self.check_big_compress_buffer(size, compress)

    # Lines 873-877 of Lib/test/test_zlib.py @ 5775aa8e
    # @bigmemtest(size=_1G + 1024 * 1024, memuse=2)
    @unittest.skip(_SKIP)
    def test_big_decompress_buffer(self, size=None):
        d = zlib.decompressobj()
        decompress = lambda s: d.decompress(s) + d.flush()
        # would call: self.check_big_decompress_buffer(size, decompress)

    # Lines 880-891 of Lib/test/test_zlib.py @ 5775aa8e
    # @unittest.skipUnless(sys.maxsize > 2**32, 'requires 64bit platform')
    # @bigmemtest(size=_4G + 100, memuse=4)
    @unittest.skip(_SKIP)
    def test_64bit_compress(self, size=None):
        data = b'x' * size
        co = zlib.compressobj(0)
        do = zlib.decompressobj()
        try:
            comp = co.compress(data) + co.flush()
            uncomp = do.decompress(comp) + do.flush()
            self.assertEqual(uncomp, data)
        finally:
            comp = uncomp = data = None

    # Lines 893-905 of Lib/test/test_zlib.py @ 5775aa8e
    # @unittest.skipUnless(sys.maxsize > 2**32, 'requires 64bit platform')
    # @bigmemtest(size=_4G + 100, memuse=3)
    @unittest.skip(_SKIP)
    def test_large_unused_data(self, size=None):
        data = b'abcdefghijklmnop'
        unused = b'x' * size
        comp = zlib.compress(data) + unused
        do = zlib.decompressobj()
        try:
            uncomp = do.decompress(comp) + do.flush()
            self.assertEqual(unused, do.unused_data)
            self.assertEqual(uncomp, data)
        finally:
            unused = comp = do = None

    # Lines 907-918 of Lib/test/test_zlib.py @ 5775aa8e
    # @unittest.skipUnless(sys.maxsize > 2**32, 'requires 64bit platform')
    # @bigmemtest(size=_4G + 100, memuse=5)
    @unittest.skip(_SKIP)
    def test_large_unconsumed_tail(self, size=None):
        data = b'x' * size
        do = zlib.decompressobj()
        try:
            comp = zlib.compress(data, 0)
            uncomp = do.decompress(comp, 1) + do.flush()
            self.assertEqual(uncomp, data)
            self.assertEqual(do.unconsumed_tail, b'')
        finally:
            comp = uncomp = data = None


if __name__ == "__main__":
    unittest.main()
