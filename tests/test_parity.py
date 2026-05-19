"""Surface-level parity between zlib_py and the stdlib zlib module.

Stubs raise NotImplementedError on call; no test here actually invokes them.
This file only checks that every public name CPython's zlib exposes is also
exposed by zlib_py, with the right kind (int, str, callable, class, exception)
and — for int constants — the right value.
"""

import sys

import zlib

import zlib_py

INT_CONSTANTS = {
    "Z_NO_COMPRESSION": 0,
    "Z_BEST_SPEED": 1,
    "Z_BEST_COMPRESSION": 9,
    "Z_DEFAULT_COMPRESSION": -1,
    "Z_FILTERED": 1,
    "Z_HUFFMAN_ONLY": 2,
    "Z_RLE": 3,
    "Z_FIXED": 4,
    "Z_DEFAULT_STRATEGY": 0,
    "Z_NO_FLUSH": 0,
    "Z_PARTIAL_FLUSH": 1,
    "Z_SYNC_FLUSH": 2,
    "Z_FULL_FLUSH": 3,
    "Z_FINISH": 4,
    "Z_BLOCK": 5,
    "Z_TREES": 6,
    "MAX_WBITS": 15,
    "DEFLATED": 8,
    "DEF_BUF_SIZE": 16384,
    "DEF_MEM_LEVEL": 8,
}
STR_CONSTANTS = ("ZLIB_VERSION", "ZLIB_RUNTIME_VERSION")
FUNCTIONS_BASE = (
    "adler32",
    "crc32",
    "compress",
    "decompress",
    "compressobj",
    "decompressobj",
)
# Added in CPython 3.14. zlib_py always exposes them; stdlib only on 3.14+.
FUNCTIONS_3_14 = ("adler32_combine", "crc32_combine")
EXCEPTIONS = ("error",)

COMPRESS_METHODS = ("compress", "flush", "copy")
DECOMPRESS_METHODS = ("decompress", "flush", "copy")
DECOMPRESS_ATTRS = ("unused_data", "unconsumed_tail", "eof", "needs_input")

EXPECTED_PUBLIC = (
    set(INT_CONSTANTS)
    | set(STR_CONSTANTS)
    | set(FUNCTIONS_BASE)
    | set(FUNCTIONS_3_14)
    | set(EXCEPTIONS)
)


def _public(mod):
    return {n for n in dir(mod) if not n.startswith("_")}


def test_stdlib_public_is_subset_of_expected():
    """If CPython's zlib grows a public name we don't know about, fail loudly
    so we can add it to the enumeration."""
    extras_in_stdlib = _public(zlib) - EXPECTED_PUBLIC
    assert not extras_in_stdlib, (
        f"stdlib zlib has names we don't track: {sorted(extras_in_stdlib)}"
    )


def test_zlib_py_public_matches_expected():
    """zlib_py exposes exactly the names we declare — no missing, no extras."""
    actual = _public(zlib_py)
    missing = EXPECTED_PUBLIC - actual
    extras = actual - EXPECTED_PUBLIC
    assert not missing, f"zlib_py is missing: {sorted(missing)}"
    assert not extras, f"zlib_py exposes extras: {sorted(extras)}"


def test_int_constants():
    for name, value in INT_CONSTANTS.items():
        assert getattr(zlib_py, name) == value, name


def test_str_constants_present():
    for name in STR_CONSTANTS:
        v = getattr(zlib_py, name)
        assert isinstance(v, str), name


def test_functions_callable():
    for name in FUNCTIONS_BASE + FUNCTIONS_3_14:
        assert callable(getattr(zlib_py, name)), name


def test_error_is_exception():
    assert issubclass(zlib_py.error, Exception)


def test_compress_class_shape():
    cls = zlib_py._Compress
    assert isinstance(cls, type)
    for name in COMPRESS_METHODS:
        assert callable(getattr(cls, name)), name


def test_decompress_class_shape():
    cls = zlib_py._Decompress
    assert isinstance(cls, type)
    for name in DECOMPRESS_METHODS:
        assert callable(getattr(cls, name)), name
    for attr in DECOMPRESS_ATTRS:
        assert hasattr(cls, attr), attr


def test_combine_functions_match_stdlib_when_available():
    """When stdlib has the 3.14 combine functions, zlib_py must too. (zlib_py
    always exposes them; this asserts presence parity.)"""
    if sys.version_info >= (3, 14):
        for name in FUNCTIONS_3_14:
            assert hasattr(zlib, name), f"stdlib zlib missing {name} on 3.14+"
            assert hasattr(zlib_py, name), name


def test_zlib_decompressor_class_shape():
    """_ZlibDecompressor was added to stdlib in 3.12. zlib_py always exposes
    it; this asserts presence parity (and that stdlib carries it on 3.12+)."""
    cls = zlib_py._ZlibDecompressor
    assert isinstance(cls, type)
    assert callable(getattr(cls, "decompress"))
    for attr in ("eof", "unused_data", "needs_input"):
        assert hasattr(cls, attr), attr
    if sys.version_info >= (3, 12):
        assert hasattr(zlib, "_ZlibDecompressor"), "stdlib zlib missing _ZlibDecompressor on 3.12+"
