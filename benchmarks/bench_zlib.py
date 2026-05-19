"""Benchmark: zlib_py (Rust, this repo) vs CPython zlib.

Vendored from farhaanaliii/zlib-rs-python @ benchmarks/bench_zlib.py
(commit `main`, fetched 2026-05-19). Only edits: rebind `zlib_rs` →
`zlib_py` and update labels. The benchmark methodology, sizes, levels,
and iteration counts are upstream's.

Compares performance across:
  - One-shot compress / decompress
  - Streaming compress / decompress
  - Checksum computation (adler32, crc32)
  - Various data sizes (1KB, 64KB, 1MB, 10MB)
  - Multiple compression levels (1, 6, 9)

Run with:

    ./result-test/bin/python benchmarks/bench_zlib.py

(or any interpreter that has both stdlib zlib and `zlib_py` installed).
"""

import os
import sys
import time
import zlib as cpython_zlib
import statistics

try:
    import zlib_py as rust_zlib
except ImportError:
    print("ERROR: zlib_py not installed. Run `nix build .#testEnv` or `pip install -e .` first.")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def generate_text_data(size: int) -> bytes:
    """Generate semi-realistic compressible text data."""
    base = (
        b"The quick brown fox jumps over the lazy dog. "
        b"Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
        b"Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. "
        b"Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris. "
    )
    repeats = (size // len(base)) + 1
    return (base * repeats)[:size]


def generate_binary_data(size: int) -> bytes:
    """Generate random (incompressible) binary data."""
    return os.urandom(size)


def bench(fn, iterations: int = 10, warmup: int = 2):
    """Run fn() for warmup + iterations and return median time in seconds."""
    for _ in range(warmup):
        fn()

    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        fn()
        elapsed = time.perf_counter() - start
        times.append(elapsed)

    return statistics.median(times)


def fmt_time(seconds: float) -> str:
    """Format seconds into a human-readable string."""
    if seconds < 1e-3:
        return f"{seconds * 1e6:8.1f} us"
    elif seconds < 1.0:
        return f"{seconds * 1e3:8.2f} ms"
    else:
        return f"{seconds:8.3f}  s"


def fmt_speedup(ratio: float) -> str:
    """Format speedup ratio with indicator."""
    if ratio > 1.05:
        return f"{ratio:5.2f}x faster"
    elif ratio < 0.95:
        return f"{1/ratio:5.2f}x slower"
    else:
        return f"  ~1.00x same"


def fmt_size(size: int) -> str:
    """Format byte size into human-readable string."""
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size // 1024} KB"
    else:
        return f"{size // (1024 * 1024)} MB"


# ---------------------------------------------------------------------------
# Benchmark definitions
# ---------------------------------------------------------------------------

DATA_SIZES = [
    1 * 1024,         # 1 KB
    64 * 1024,        # 64 KB
    1 * 1024 * 1024,  # 1 MB
    10 * 1024 * 1024, # 10 MB
]

COMPRESSION_LEVELS = [1, 6, 9]

SEPARATOR = "-" * 100
HEADER_FMT = "{:<40s} {:>14s} {:>14s} {:>16s}"
ROW_FMT = "{:<40s} {:>14s} {:>14s} {:>16s}"


def print_header(title: str):
    print()
    print(SEPARATOR)
    print(f"  {title}")
    print(SEPARATOR)
    print(HEADER_FMT.format("Benchmark", "CPython zlib", "zlib_py", "Speedup"))
    print(SEPARATOR)


def print_row(name: str, cpython_time: float, rust_time: float):
    speedup = cpython_time / rust_time if rust_time > 0 else float("inf")
    print(ROW_FMT.format(
        name,
        fmt_time(cpython_time),
        fmt_time(rust_time),
        fmt_speedup(speedup),
    ))


def run_oneshot_compress_benchmarks():
    """Benchmark one-shot compression at various sizes and levels."""
    print_header("ONE-SHOT COMPRESSION")

    for size in DATA_SIZES:
        data = generate_text_data(size)
        for level in COMPRESSION_LEVELS:
            iters = max(3, 500 // (size // 1024 + 1))
            name = f"compress  {fmt_size(size):>5s}  level={level}"
            t_cpython = bench(lambda: cpython_zlib.compress(data, level), iterations=iters)
            t_rust = bench(lambda: rust_zlib.compress(data, level), iterations=iters)
            print_row(name, t_cpython, t_rust)


def run_oneshot_decompress_benchmarks():
    """Benchmark one-shot decompression at various sizes."""
    print_header("ONE-SHOT DECOMPRESSION")

    for size in DATA_SIZES:
        data = generate_text_data(size)
        for level in COMPRESSION_LEVELS:
            compressed_cpython = cpython_zlib.compress(data, level)
            compressed_rust = rust_zlib.compress(data, level)

            iters = max(3, 500 // (size // 1024 + 1))
            name = f"decompress  {fmt_size(size):>5s}  level={level}"
            t_cpython = bench(
                lambda: cpython_zlib.decompress(compressed_cpython),
                iterations=iters,
            )
            t_rust = bench(
                lambda: rust_zlib.decompress(compressed_rust, 15, size * 2),
                iterations=iters,
            )
            print_row(name, t_cpython, t_rust)


def run_streaming_compress_benchmarks():
    """Benchmark streaming compression."""
    print_header("STREAMING COMPRESSION")

    chunk_size = 16384
    for size in DATA_SIZES:
        data = generate_text_data(size)
        level = 6
        iters = max(3, 200 // (size // 1024 + 1))

        def cpython_streaming():
            c = cpython_zlib.compressobj(level)
            out = []
            for i in range(0, len(data), chunk_size):
                out.append(c.compress(data[i:i + chunk_size]))
            out.append(c.flush())
            return b"".join(out)

        def rust_streaming():
            c = rust_zlib.compressobj(level)
            out = []
            for i in range(0, len(data), chunk_size):
                out.append(c.compress(data[i:i + chunk_size]))
            out.append(c.flush())
            return b"".join(out)

        name = f"stream compress  {fmt_size(size):>5s}  L6"
        t_cpython = bench(cpython_streaming, iterations=iters)
        t_rust = bench(rust_streaming, iterations=iters)
        print_row(name, t_cpython, t_rust)


def run_streaming_decompress_benchmarks():
    """Benchmark streaming decompression."""
    print_header("STREAMING DECOMPRESSION")

    chunk_size = 16384
    for size in DATA_SIZES:
        data = generate_text_data(size)
        compressed = cpython_zlib.compress(data, 6)
        iters = max(3, 200 // (size // 1024 + 1))

        def cpython_streaming():
            d = cpython_zlib.decompressobj()
            out = []
            for i in range(0, len(compressed), chunk_size):
                out.append(d.decompress(compressed[i:i + chunk_size]))
            return b"".join(out)

        def rust_streaming():
            d = rust_zlib.decompressobj()
            out = []
            for i in range(0, len(compressed), chunk_size):
                out.append(d.decompress(compressed[i:i + chunk_size]))
            return b"".join(out)

        name = f"stream decompress  {fmt_size(size):>5s}  L6"
        t_cpython = bench(cpython_streaming, iterations=iters)
        t_rust = bench(rust_streaming, iterations=iters)
        print_row(name, t_cpython, t_rust)


def run_checksum_benchmarks():
    """Benchmark adler32 and crc32 checksums."""
    print_header("CHECKSUMS")

    for size in DATA_SIZES:
        data = generate_text_data(size)
        iters = max(5, 1000 // (size // 1024 + 1))

        name = f"adler32  {fmt_size(size):>5s}"
        t_cpython = bench(lambda: cpython_zlib.adler32(data), iterations=iters)
        t_rust = bench(lambda: rust_zlib.adler32(data), iterations=iters)
        print_row(name, t_cpython, t_rust)

        name = f"crc32    {fmt_size(size):>5s}"
        t_cpython = bench(lambda: cpython_zlib.crc32(data), iterations=iters)
        t_rust = bench(lambda: rust_zlib.crc32(data), iterations=iters)
        print_row(name, t_cpython, t_rust)


def run_binary_compress_benchmarks():
    """Benchmark compression on random (incompressible) binary data."""
    print_header("BINARY DATA COMPRESSION (incompressible)")

    for size in [64 * 1024, 1 * 1024 * 1024]:
        data = generate_binary_data(size)
        level = 6
        iters = max(3, 200 // (size // 1024 + 1))

        name = f"compress binary  {fmt_size(size):>5s}  L6"
        t_cpython = bench(lambda: cpython_zlib.compress(data, level), iterations=iters)
        t_rust = bench(lambda: rust_zlib.compress(data, level), iterations=iters)
        print_row(name, t_cpython, t_rust)


def run_compression_ratio_comparison():
    """Compare compression ratios between the two implementations."""
    print()
    print(SEPARATOR)
    print("  COMPRESSION RATIO COMPARISON")
    print(SEPARATOR)
    ratio_header = "{:<30s} {:>10s} {:>14s} {:>14s} {:>14s}"
    ratio_row = "{:<30s} {:>10s} {:>14s} {:>14s} {:>14s}"
    print(ratio_header.format("Data", "Original", "CPython", "zlib_py", "Match?"))
    print(SEPARATOR)

    for size in [1024, 64 * 1024, 1024 * 1024]:
        data = generate_text_data(size)
        for level in [1, 6, 9]:
            c_cpython = cpython_zlib.compress(data, level)
            c_rust = rust_zlib.compress(data, level)
            match = "YES" if len(c_cpython) == len(c_rust) else "close" if abs(len(c_cpython) - len(c_rust)) < 100 else "NO"
            name = f"text {fmt_size(size)} L{level}"
            print(ratio_row.format(
                name,
                fmt_size(size),
                fmt_size(len(c_cpython)),
                fmt_size(len(c_rust)),
                match,
            ))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 100)
    print("  BENCHMARK: zlib_py (Rust) vs CPython zlib")
    print(f"  Python {sys.version}")
    print(f"  zlib_py runtime: {getattr(rust_zlib, 'ZLIB_RUNTIME_VERSION', 'unknown')}")
    print("=" * 100)

    run_oneshot_compress_benchmarks()
    run_oneshot_decompress_benchmarks()
    run_streaming_compress_benchmarks()
    run_streaming_decompress_benchmarks()
    run_checksum_benchmarks()
    run_binary_compress_benchmarks()
    run_compression_ratio_comparison()

    print()
    print(SEPARATOR)
    print("  DONE")
    print(SEPARATOR)


if __name__ == "__main__":
    main()
