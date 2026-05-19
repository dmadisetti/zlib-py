"""zlib-rs bindings for Python.

This package wraps the compiled extension at `zlib_py.zlib_py` and re-exports
everything to the top-level `zlib_py` namespace so users see the same flat
surface as the stdlib `zlib` module.
"""

from .zlib_py import *  # noqa: F401,F403
# `import *` skips underscore-prefixed names; pull them in explicitly.
from .zlib_py import _Compress, _Decompress  # noqa: F401

# Python's import machinery binds the submodule onto the package as
# `zlib_py.zlib_py` whenever we do a relative import like the one above. That
# leaks an extra name into `dir(zlib_py)`. Drop it so the public surface
# matches stdlib `zlib`.
del zlib_py  # type: ignore[name-defined]


def __getattr__(name):
    # Mirrors CPython's deprecation of `zlib.__version__` (slated for 3.20).
    # Module-level __getattr__ keeps the name out of `dir()` while still
    # serving the access with the spec-mandated DeprecationWarning.
    if name == "__version__":
        import warnings
        warnings.warn(
            "'__version__' is deprecated and slated for removal in Python 3.20",
            DeprecationWarning,
            stacklevel=2,
        )
        return ZLIB_VERSION  # noqa: F821
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
