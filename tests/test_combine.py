"""Combine tests vendored from CPython's Lib/test/test_zlib.py.

Source: https://github.com/python/cpython/blob/5775aa8e295102156de14fd1ba284722c6ede95a/Lib/test/test_zlib.py
Commit: 5775aa8e295102156de14fd1ba284722c6ede95a (3.16-alpha)

`adler32_combine` and `crc32_combine` are 3.14+ APIs in stdlib zlib, but
zlib_py always exposes them (zlib-rs 0.6.3 has the helpers regardless of
host Python version), so the vendored test bodies run unconditionally
here. The version gate only lives in tests/test_parity.py, where we
compare module surfaces against stdlib.
"""

import random
import unittest

import zlib_py as zlib  # so vendored bodies run against our module unmodified


# Lines 122-205 of Lib/test/test_zlib.py @ 5775aa8e
class ChecksumCombineMixin:
    """Mixin class for testing checksum combination."""

    N = 1000
    default_iv: int

    def parse_iv(self, iv):
        """Parse an IV value.

        - The default IV is returned if *iv* is None.
        - A random IV is returned if *iv* is -1.
        - Otherwise, *iv* is returned as is.
        """
        if iv is None:
            return self.default_iv
        if iv == -1:
            return random.randint(1, 0x80000000)
        return iv

    def checksum(self, data, init=None):
        """Compute the checksum of data with a given initial value.

        The *init* value is parsed by ``parse_iv``.
        """
        iv = self.parse_iv(init)
        return self._checksum(data, iv)

    def _checksum(self, data, init):
        raise NotImplementedError

    def combine(self, a, b, blen):
        """Combine two checksums together."""
        raise NotImplementedError

    def get_random_data(self, data_len, *, iv=None):
        """Get a triplet (data, iv, checksum)."""
        data = random.randbytes(data_len)
        init = self.parse_iv(iv)
        checksum = self.checksum(data, init)
        return data, init, checksum

    def test_combine_empty(self):
        for _ in range(self.N):
            a, iv, checksum = self.get_random_data(32, iv=-1)
            res = self.combine(iv, self.checksum(a), len(a))
            self.assertEqual(res, checksum)

    def test_combine_no_iv(self):
        for _ in range(self.N):
            a, _, chk_a = self.get_random_data(32)
            b, _, chk_b = self.get_random_data(64)
            res = self.combine(chk_a, chk_b, len(b))
            self.assertEqual(res, self.checksum(a + b))

    def test_combine_no_iv_invalid_length(self):
        a, _, chk_a = self.get_random_data(32)
        b, _, chk_b = self.get_random_data(64)
        checksum = self.checksum(a + b)
        for invalid_len in [1, len(a), 48, len(b) + 1, 191]:
            invalid_res = self.combine(chk_a, chk_b, invalid_len)
            self.assertNotEqual(invalid_res, checksum)

        self.assertRaises(TypeError, self.combine, 0, 0, "len")

    def test_combine_with_iv(self):
        for _ in range(self.N):
            a, iv_a, chk_a_with_iv = self.get_random_data(32, iv=-1)
            chk_a_no_iv = self.checksum(a)
            b, iv_b, chk_b_with_iv = self.get_random_data(64, iv=-1)
            chk_b_no_iv = self.checksum(b)

            # We can represent c = COMBINE(CHK(a, iv_a), CHK(b, iv_b)) as:
            #
            #   c = CHK(CHK(b'', iv_a) + CHK(a) + CHK(b'', iv_b) + CHK(b))
            #     = COMBINE(
            #           COMBINE(CHK(b'', iv_a), CHK(a)),
            #           COMBINE(CHK(b'', iv_b), CHK(b)),
            #       )
            #     = COMBINE(COMBINE(iv_a, CHK(a)), COMBINE(iv_b, CHK(b)))
            tmp0 = self.combine(iv_a, chk_a_no_iv, len(a))
            tmp1 = self.combine(iv_b, chk_b_no_iv, len(b))
            expected = self.combine(tmp0, tmp1, len(b))
            checksum = self.combine(chk_a_with_iv, chk_b_with_iv, len(b))
            self.assertEqual(checksum, expected)


# Lines 208-216 of Lib/test/test_zlib.py @ 5775aa8e
class CRC32CombineTestCase(ChecksumCombineMixin, unittest.TestCase):

    default_iv = 0

    def _checksum(self, data, init):
        return zlib.crc32(data, init)

    def combine(self, a, b, blen):
        return zlib.crc32_combine(a, b, blen)


# Lines 219-227 of Lib/test/test_zlib.py @ 5775aa8e
class Adler32CombineTestCase(ChecksumCombineMixin, unittest.TestCase):

    default_iv = 1

    def _checksum(self, data, init):
        return zlib.adler32(data, init)

    def combine(self, a, b, blen):
        return zlib.adler32_combine(a, b, blen)


if __name__ == "__main__":
    unittest.main()
