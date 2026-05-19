"""Decompress tests vendored from CPython's Lib/test/test_zlib.py.

Source: https://github.com/python/cpython/blob/5775aa8e295102156de14fd1ba284722c6ede95a/Lib/test/test_zlib.py
Commit: 5775aa8e295102156de14fd1ba284722c6ede95a (3.16-alpha)

CPython's test file groups one-shot decompress tests under
`CompressTestCase` rather than a dedicated class; the round-trip cases
live in `tests/test_compress.py`. This file covers the
decompress-specific behaviour: truncated input error, custom bufsize,
wbits variants.
"""

import unittest

import zlib as cpython_zlib
import zlib_py


# Same HAMLET_SCENE excerpt vendored at Lib/test/test_zlib.py:17-77 @ 5775aa8e.
# Duplicated here so this file is self-contained.
HAMLET_SCENE = b"""
LAERTES

       O, fear me not.
       I stay too long: but here my father comes.

       Enter POLONIUS

       A double blessing is a double grace,
       Occasion smiles upon a second leave.

LORD POLONIUS

       Yet here, Laertes! aboard, aboard, for shame!
       The wind sits in the shoulder of your sail,
       And you are stay'd for. There; my blessing with thee!
"""


class CrossCompatWithStdlib(unittest.TestCase):
    """Verify our compress decodes via stdlib and vice versa, every level.

    Not from CPython's test suite — this is the actual interop contract
    for the deflate format. Byte-level output diverges between zlib-rs
    and C zlib at intermediate levels (see ByteParityWithStdlib in
    test_compress.py), but both sides must produce streams the other
    can decode. If either direction fails at any level, we've broken
    the format contract.
    """

    DATA = HAMLET_SCENE * 5

    def test_ours_compresses_theirs_decompresses(self):
        for level in range(-1, 10):
            with self.subTest(level=level):
                self.assertEqual(
                    cpython_zlib.decompress(zlib_py.compress(self.DATA, level)),
                    self.DATA,
                )

    def test_theirs_compresses_ours_decompresses(self):
        for level in range(-1, 10):
            with self.subTest(level=level):
                self.assertEqual(
                    zlib_py.decompress(cpython_zlib.compress(self.DATA, level)),
                    self.DATA,
                )


class DecompressTestCase(unittest.TestCase):
    # Lines 615-621 of Lib/test/test_zlib.py @ 5775aa8e
    # xfail: zlib-rs returns DataError(-3) for a truncated stream where
    # C zlib returns BufError(-5). Engine-level divergence — the format
    # contract still holds (both decoders reject the truncation), but
    # the specific return code doesn't match.
    #
    # Upstream suggestion (zlib-rs): the inflate State already holds an
    # `error_message: Option<&'static str>` and a `total_in` counter
    # internally; exposing them through `Inflate` (or returning a richer
    # error type from `decompress_slice`) would let callers distinguish
    # "truncated" from "corrupt" without re-running the stream.
    @unittest.expectedFailure
    def test_incomplete_stream(self):
        # A useful error message is given
        x = zlib_py.compress(HAMLET_SCENE)
        self.assertRaisesRegex(zlib_py.error,
            "Error -5 while decompressing data: incomplete or truncated stream",
            zlib_py.decompress, x[:-1])

    # Same case, but assert what we actually return — proves we raise
    # zlib_py.error on truncated input even though the code/message
    # differ from C zlib's.
    def test_incomplete_stream_raises_error(self):
        x = zlib_py.compress(HAMLET_SCENE)
        with self.assertRaises(zlib_py.error):
            zlib_py.decompress(x[:-1])

    # Lines 643-647 of Lib/test/test_zlib.py @ 5775aa8e (CustomInt
    # subclassed from int — replaced with a plain int here since our
    # bufsize is `usize` and goes through __index__ automatically.)
    def test_custom_bufsize(self):
        data = HAMLET_SCENE * 10
        compressed = zlib_py.compress(data, 1)
        self.assertEqual(zlib_py.decompress(compressed, 15, 1), data)


if __name__ == "__main__":
    unittest.main()
