#![allow(non_camel_case_types, non_snake_case, unused_variables)]

//! zlib-rs bindings for Python.
//!
//! Stub phase: every name CPython's `zlib` exposes is present, but the
//! callable bodies all raise `NotImplementedError`. Filled in
//! function-by-function in subsequent commits — see CONVERSION.md.

use std::sync::Mutex;

use pyo3::buffer::PyBuffer;
use pyo3::create_exception;
use pyo3::exceptions::{PyBufferError, PyException, PyNotImplementedError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyBytes;
use zlib_rs::{Deflate, DeflateFlush, Inflate, InflateFlush, Status};

/// Validate wbits for one-shot compress / streaming compressobj.
/// Accepts -15..=-8 (raw), 8..=15 (zlib), 25..=31 (gzip).
///
/// CPython's zlibmodule.c maps zlib's Z_STREAM_ERROR (returned by
/// deflateInit2 for out-of-range wbits) to `PyExc_ValueError`, not
/// `zlib.error`, so we do the same.
fn validate_compress_wbits(wbits: i32) -> PyResult<()> {
    if (-15..=-8).contains(&wbits) || (8..=15).contains(&wbits) || (25..=31).contains(&wbits) {
        Ok(())
    } else {
        Err(PyValueError::new_err("Invalid initialization option"))
    }
}

/// Validate wbits for one-shot decompress / streaming decompressobj.
/// Accepts the compress range plus 0 (use header) and 40..=47 (auto-detect).
/// Mirrors zlib's inflateInit2 windowBits encoding: low 4 bits = window size,
/// high bits = wrap mode (0=zlib, 16=gzip, 32=auto).
fn validate_decompress_wbits(wbits: i32) -> PyResult<()> {
    if wbits == 0
        || (-15..=-8).contains(&wbits)
        || (8..=15).contains(&wbits)
        || (24..=31).contains(&wbits)
        || (40..=47).contains(&wbits)
    {
        Ok(())
    } else {
        Err(PyValueError::new_err("Invalid initialization option"))
    }
}

/// Lookup table from zlib-rs `ReturnCode` to (numeric code, symbolic name,
/// human message). The numeric codes match C zlib's 1:1 so existing
/// zlib-format error regexes can match our messages.
///
/// **Divergence note.** C zlib distinguishes two failure modes that
/// zlib-rs collapses:
/// - `Z_BUF_ERROR` (-5): inflate ran out of input mid-stream (truncation)
///   *or* output buffer full with no progress possible.
/// - `Z_DATA_ERROR` (-3): corrupt deflate (bad huffman, bad CRC, etc.).
///
/// zlib-rs reports both as `DataError(-3)`. Callers that need to
/// distinguish "truncated" from "corrupt" can't, regardless of what
/// message we attach here. See `tests/test_decompress.py::DecompressTestCase::test_incomplete_stream`
/// for the test this affects.
fn return_code_info(rc: zlib_rs::ReturnCode) -> (i32, &'static str, &'static str) {
    use zlib_rs::ReturnCode::*;
    match rc {
        Ok           => ( 0, "Z_OK",            ""),
        StreamEnd    => ( 1, "Z_STREAM_END",    ""),
        NeedDict     => ( 2, "Z_NEED_DICT",     "preset dictionary required"),
        ErrNo        => (-1, "Z_ERRNO",         "io error"),
        StreamError  => (-2, "Z_STREAM_ERROR",  "invalid stream state"),
        DataError    => (-3, "Z_DATA_ERROR",    "invalid or incomplete data"),
        MemError     => (-4, "Z_MEM_ERROR",     "out of memory"),
        BufError     => (-5, "Z_BUF_ERROR",     "incomplete or truncated stream"),
        VersionError => (-6, "Z_VERSION_ERROR", "incompatible zlib version"),
    }
}

/// Get a contiguous `&[u8]` view of a buffer-protocol object.
/// Caller must keep the PyBuffer alive for the slice's lifetime.
fn buffer_as_slice<'a>(buf: &'a PyBuffer<u8>) -> PyResult<&'a [u8]> {
    if !buf.is_c_contiguous() {
        return Err(PyBufferError::new_err("buffer must be C-contiguous"));
    }
    Ok(unsafe { std::slice::from_raw_parts(buf.buf_ptr() as *const u8, buf.item_count()) })
}

create_exception!(zlib_py, error, PyException);

// ---- module-level functions -------------------------------------------------

#[pyfunction]
#[pyo3(signature = (data, value=1, /))]
fn adler32(data: &Bound<'_, PyAny>, value: u32) -> PyResult<u32> {
    let buf = PyBuffer::<u8>::get(data)?;
    if !buf.is_c_contiguous() {
        return Err(PyBufferError::new_err(
            "buffer must be C-contiguous",
        ));
    }
    // PyBuffer keeps the underlying storage pinned for its lifetime, so this
    // slice is safe to read from. We don't release the GIL: adler32 is a
    // tight SIMD loop and the overhead of releasing+re-acquiring dwarfs the
    // compute for any input small enough to be common.
    let slice = unsafe {
        std::slice::from_raw_parts(buf.buf_ptr() as *const u8, buf.item_count())
    };
    Ok(zlib_rs::adler32::adler32(value, slice))
}

#[pyfunction]
#[pyo3(signature = (data, value=0, /))]
fn crc32(data: &Bound<'_, PyAny>, value: u32) -> PyResult<u32> {
    let buf = PyBuffer::<u8>::get(data)?;
    if !buf.is_c_contiguous() {
        return Err(PyBufferError::new_err(
            "buffer must be C-contiguous",
        ));
    }
    let slice = unsafe {
        std::slice::from_raw_parts(buf.buf_ptr() as *const u8, buf.item_count())
    };
    Ok(zlib_rs::crc32::crc32(value, slice))
}

// CPython's adler32_combine / crc32_combine route `len2` through
// `Py_off_t_converter`, which accepts any Python int (incl. negatives)
// and the C zlib functions cast it through `z_off_t`. We mirror that by
// accepting i64 here and reinterpreting to u64 — matches C's cast and
// stays spec-compatible. zlib-rs 0.6.3 exposes both combine helpers
// publicly so no hand-rolling needed.
#[pyfunction]
#[pyo3(signature = (adler1, adler2, len2, /))]
fn adler32_combine(adler1: u32, adler2: u32, len2: i64) -> PyResult<u32> {
    Ok(zlib_rs::adler32::adler32_combine(adler1, adler2, len2 as u64))
}

#[pyfunction]
#[pyo3(signature = (crc1, crc2, len2, /))]
fn crc32_combine(crc1: u32, crc2: u32, len2: i64) -> PyResult<u32> {
    Ok(zlib_rs::crc32::crc32_combine(crc1, crc2, len2 as u64))
}

#[pyfunction]
#[pyo3(signature = (data, /, level=-1, wbits=15))]
fn compress(
    py: Python<'_>,
    data: &Bound<'_, PyAny>,
    level: i32,
    wbits: i32,
) -> PyResult<Py<PyBytes>> {
    // CPython's one-shot compress() routes invalid level / wbits through
    // deflateInit2 and maps the resulting Z_STREAM_ERROR to zlib.error —
    // not ValueError. (compressobj() does map to ValueError; see below.)
    // No upfront validation here; let compress_slice report.
    let buf = PyBuffer::<u8>::get(data)?;
    let input = buffer_as_slice(&buf)?;

    let mut config = zlib_rs::DeflateConfig::new(level);
    config.window_bits = wbits;

    let bound = zlib_rs::compress_bound(input.len());
    let mut output = vec![0u8; bound];
    let (compressed, rc) = zlib_rs::compress_slice(&mut output, input, config);
    match rc {
        zlib_rs::ReturnCode::Ok | zlib_rs::ReturnCode::StreamEnd => {
            let n = compressed.len();
            Ok(PyBytes::new(py, &output[..n]).unbind())
        }
        _ => {
            let (code, _, msg) = return_code_info(rc);
            Err(error::new_err(format!(
                "Error {} while compressing data: {}",
                code, msg,
            )))
        }
    }
}

#[pyfunction]
#[pyo3(signature = (data, /, wbits=15, bufsize=16384))]
fn decompress(
    py: Python<'_>,
    data: &Bound<'_, PyAny>,
    wbits: i32,
    bufsize: usize,
) -> PyResult<Py<PyBytes>> {
    validate_decompress_wbits(wbits)?;
    let buf = PyBuffer::<u8>::get(data)?;
    let input = buffer_as_slice(&buf)?;

    let config = zlib_rs::InflateConfig { window_bits: wbits };
    // Start at bufsize literally (spec: bufsize is the initial buffer; 0 is
    // coerced to 1). Double on BufError, no fixed cap — caller's RAM is the
    // limit, not us.
    let mut size = bufsize.max(1);
    loop {
        let mut output = vec![0u8; size];
        let (decompressed, rc) = zlib_rs::decompress_slice(&mut output, input, config);
        match rc {
            zlib_rs::ReturnCode::Ok | zlib_rs::ReturnCode::StreamEnd => {
                let n = decompressed.len();
                return Ok(PyBytes::new(py, &output[..n]).unbind());
            }
            zlib_rs::ReturnCode::BufError => {
                size = size.checked_mul(2).ok_or_else(|| {
                    error::new_err("decompression output exceeds usize::MAX bytes")
                })?;
            }
            _ => {
                let (code, _, msg) = return_code_info(rc);
                return Err(error::new_err(format!(
                    "Error {} while decompressing data: {}",
                    code, msg,
                )));
            }
        }
    }
}

#[pyfunction]
#[pyo3(signature = (level=-1, method=8, wbits=15, memLevel=8, strategy=0, zdict=None))]
fn compressobj(
    level: i32,
    method: i32,
    wbits: i32,
    memLevel: i32,
    strategy: i32,
    zdict: Option<&Bound<'_, PyAny>>,
) -> PyResult<Compress> {
    if level != -1 && !(0..=9).contains(&level) {
        return Err(PyValueError::new_err("Bad compression level"));
    }
    if method != 8 {
        return Err(error::new_err("Bad compression method"));
    }
    if (25..=31).contains(&wbits) {
        // zlib-rs 0.6.3's stable Deflate::new doesn't surface the gzip wrap
        // mode that wbits >= 16 selects in C zlib (DeflateStream::new accepts
        // the full DeflateConfig but is pub(crate)). Bail honestly rather
        // than silently emitting a zlib-wrapped stream when gzip was asked.
        return Err(error::new_err(
            "gzip wbits (25..=31) not supported by compressobj() in this build; \
             use compress() one-shot for gzip output",
        ));
    }
    validate_compress_wbits(wbits)?;
    // memLevel and strategy are accepted for API parity but currently
    // ignored — zlib-rs stable Deflate constructor doesn't surface them.
    // Tracked as deviation #5 in THIRD_PARTY.md.
    let _ = memLevel;
    let _ = strategy;

    let (zlib_header, window_bits) = if wbits < 0 {
        (false, (-wbits) as u8)
    } else {
        (true, wbits as u8)
    };
    let mut deflate = Deflate::new(level, zlib_header, window_bits);

    if let Some(d) = zdict {
        let buf = PyBuffer::<u8>::get(d)?;
        let dict = buffer_as_slice(&buf)?;
        deflate.set_dictionary(dict).map_err(|e| {
            error::new_err(format!("setting dictionary failed: {:?}", e))
        })?;
    }

    Ok(Compress {
        state: Mutex::new(CompressState {
            deflate: Some(deflate),
            buf: Vec::with_capacity(32768),
        }),
    })
}

#[pyfunction]
#[pyo3(signature = (wbits=15, zdict=None))]
fn decompressobj(wbits: i32, zdict: Option<&Bound<'_, PyAny>>) -> PyResult<Decompress> {
    // Inflate::new can only build zlib (positive bool) or raw (negative
    // window_bits) streams. Gzip wrap and auto-detect aren't reachable
    // from the public streaming API. Same asymmetry as compressobj —
    // honest error, not silent corruption.
    if (24..=31).contains(&wbits) || (40..=47).contains(&wbits) {
        return Err(error::new_err(
            "gzip / auto-detect wbits not supported by decompressobj() in this \
             build; use decompress() one-shot for those formats",
        ));
    }
    if !((-15..=-8).contains(&wbits) || (8..=15).contains(&wbits) || wbits == 0) {
        return Err(PyValueError::new_err("Invalid initialization option"));
    }
    let (zlib_header, window_bits) = if wbits == 0 {
        // wbits=0 means "use header's window size" — Inflate::new doesn't
        // surface that; pass max (15) and rely on the header to constrain.
        (true, 15u8)
    } else if wbits < 0 {
        (false, (-wbits) as u8)
    } else {
        (true, wbits as u8)
    };
    let inflate = Inflate::new(zlib_header, window_bits);
    // For zlib-format streams, set_dictionary fails with StreamError until
    // the decompressor has consumed the zlib header and asked for the
    // dictionary (NeedDict). Stash the dict and apply on demand from
    // inside decompress().
    let zdict = match zdict {
        Some(d) => {
            let buf = PyBuffer::<u8>::get(d)?;
            Some(buffer_as_slice(&buf)?.to_vec())
        }
        None => None,
    };
    let mut state = DecompressState {
        inflate,
        buf: Vec::with_capacity(32768),
        unused_data: Vec::new(),
        unconsumed_tail: Vec::new(),
        eof: false,
        needs_input: true,
        zdict,
    };
    // Raw deflate streams (no header) don't trigger NeedDict — set the
    // dict eagerly there. set_dictionary returns StreamError for the
    // zlib-header case; the dict stays stashed for later.
    if !zlib_header {
        if let Some(d) = state.zdict.as_deref() {
            let _ = state.inflate.set_dictionary(d);
        }
    }
    Ok(Decompress {
        state: Mutex::new(state),
    })
}

// ---- streaming objects ------------------------------------------------------

// Stdlib `zlib` doesn't expose `Compress`/`Decompress` as module attrs — you
// only get them via `type(compressobj())`. We expose them under underscore
// names so they're available for testing while staying out of the public
// surface. Renames to plain `Compress`/`Decompress` once `compressobj` is
// implemented and tests can reach them via `type(compressobj())`.

struct CompressState {
    /// `None` after a Z_FINISH flush — the stream is closed and any further
    /// operation must raise.
    deflate: Option<Deflate>,
    /// Reusable scratch buffer to avoid per-call allocations.
    buf: Vec<u8>,
}

fn deflate_flush_from_mode(mode: i32) -> PyResult<DeflateFlush> {
    match mode {
        0 => Ok(DeflateFlush::NoFlush),
        1 => Ok(DeflateFlush::PartialFlush),
        2 => Ok(DeflateFlush::SyncFlush),
        3 => Ok(DeflateFlush::FullFlush),
        4 => Ok(DeflateFlush::Finish),
        5 => Ok(DeflateFlush::Block),
        // Z_TREES (6) isn't a deflate flush mode in zlib — only inflate.
        _ => Err(PyValueError::new_err("Invalid flush option")),
    }
}

#[pyclass(name = "_Compress")]
pub struct Compress {
    state: Mutex<CompressState>,
}

#[pymethods]
impl Compress {
    #[pyo3(signature = (data, /))]
    fn compress(&self, py: Python<'_>, data: &Bound<'_, PyAny>) -> PyResult<Py<PyBytes>> {
        let py_buf = PyBuffer::<u8>::get(data)?;
        let input = buffer_as_slice(&py_buf)?;

        let mut guard = self.state.lock().unwrap();
        let CompressState { deflate, buf } = &mut *guard;
        let Some(deflate) = deflate.as_mut() else {
            return Err(error::new_err(
                "compressor has been flushed and cannot be reused",
            ));
        };

        let needed = zlib_rs::compress_bound(input.len()) + 64;
        if buf.len() < needed {
            buf.resize(needed, 0);
        }

        let old_total_out = deflate.total_out();
        deflate
            .compress(input, buf, DeflateFlush::NoFlush)
            .map_err(|e| error::new_err(format!("compress failed: {:?}", e)))?;
        let written = (deflate.total_out() - old_total_out) as usize;
        Ok(PyBytes::new(py, &buf[..written]).unbind())
    }

    #[pyo3(signature = (mode=4, /))]
    fn flush(&self, py: Python<'_>, mode: i32) -> PyResult<Py<PyBytes>> {
        let flush_mode = deflate_flush_from_mode(mode)?;
        // Spec: Z_NO_FLUSH on flush() is a no-op that returns empty bytes
        // immediately.
        if flush_mode == DeflateFlush::NoFlush {
            return Ok(PyBytes::new(py, b"").unbind());
        }

        let mut guard = self.state.lock().unwrap();
        let CompressState { deflate, buf } = &mut *guard;
        let Some(deflate) = deflate.as_mut() else {
            return Err(error::new_err(
                "compressor has been flushed and cannot be reused",
            ));
        };

        if buf.len() < 32768 {
            buf.resize(32768, 0);
        }

        let mut output: Vec<u8> = Vec::with_capacity(4096);
        let buf_len = buf.len();
        loop {
            let old_total_out = deflate.total_out();
            let status = deflate
                .compress(&[], buf, flush_mode)
                .map_err(|e| error::new_err(format!("flush failed: {:?}", e)))?;
            let written = (deflate.total_out() - old_total_out) as usize;
            output.extend_from_slice(&buf[..written]);
            match status {
                Status::StreamEnd => break,
                _ if written < buf_len && flush_mode != DeflateFlush::Finish => break,
                _ if written == 0 => break,
                _ => continue,
            }
        }

        if flush_mode == DeflateFlush::Finish {
            guard.deflate = None;
        }

        Ok(PyBytes::new(py, &output).unbind())
    }

    fn copy(&self) -> PyResult<Compress> {
        Err(PyNotImplementedError::new_err(
            "Compress.copy not yet supported — needs libz-rs-sys deflateCopy",
        ))
    }
}

struct DecompressState {
    inflate: Inflate,
    buf: Vec<u8>,
    unused_data: Vec<u8>,
    unconsumed_tail: Vec<u8>,
    eof: bool,
    needs_input: bool,
    /// Stashed zdict awaiting a NeedDict signal from the decoder.
    zdict: Option<Vec<u8>>,
}

#[pyclass(name = "_Decompress")]
pub struct Decompress {
    state: Mutex<DecompressState>,
}

#[pymethods]
impl Decompress {
    #[pyo3(signature = (data, /, max_length=0))]
    fn decompress(
        &self,
        py: Python<'_>,
        data: &Bound<'_, PyAny>,
        max_length: i64,
    ) -> PyResult<Py<PyBytes>> {
        if max_length < 0 {
            return Err(PyValueError::new_err(
                "max_length must be non-negative",
            ));
        }
        let max_length = max_length as usize;
        let py_buf = PyBuffer::<u8>::get(data)?;
        let new_input = buffer_as_slice(&py_buf)?;

        let mut guard = self.state.lock().unwrap();
        let state = &mut *guard;

        // Trailing data after stream end accumulates in unused_data.
        if state.eof {
            state.unused_data.extend_from_slice(new_input);
            return Ok(PyBytes::new(py, b"").unbind());
        }

        // unconsumed_tail is *reported* to the caller (CPython spec) — the
        // caller passes it back via `data`. Clearing it here means the
        // user-supplied buffer is the single source of truth and we don't
        // double-feed when they hand us `dco.unconsumed_tail` verbatim.
        state.unconsumed_tail.clear();
        let input: Vec<u8> = new_input.to_vec();

        // Per CPython: max_length=0 means "no limit" (mapped to as much as
        // we can decode in one shot, doubling on need).
        let mut output: Vec<u8> = Vec::new();
        // Cap initial allocation regardless of max_length: it's just a
        // working buffer, the inner loop refills as needed. Without the cap,
        // callers passing max_length=sys.maxsize would OOM us.
        const MAX_INITIAL_BUF: usize = 65536;
        let initial = if max_length > 0 {
            max_length.min(MAX_INITIAL_BUF)
        } else {
            16384.max(input.len() * 2).min(MAX_INITIAL_BUF)
        };
        if state.buf.len() < initial {
            state.buf.resize(initial, 0);
        }

        let mut input_pos = 0;
        loop {
            if max_length > 0 && output.len() >= max_length {
                state.unconsumed_tail = input[input_pos..].to_vec();
                break;
            }
            let want = if max_length > 0 {
                (max_length - output.len()).min(state.buf.len())
            } else {
                state.buf.len()
            };
            if want == 0 {
                break;
            }
            let chunk_in = &input[input_pos..];
            let old_total_in = state.inflate.total_in();
            let old_total_out = state.inflate.total_out();
            let result = state
                .inflate
                .decompress(chunk_in, &mut state.buf[..want], InflateFlush::NoFlush);
            let status = match result {
                Ok(s) => s,
                Err(zlib_rs::InflateError::NeedDict { .. }) => {
                    if let Some(d) = state.zdict.as_deref() {
                        // The decoder consumed the zlib header before
                        // raising NeedDict; advance input_pos so the next
                        // iteration feeds the deflate payload, not the
                        // already-parsed header bytes.
                        let consumed = (state.inflate.total_in() - old_total_in) as usize;
                        input_pos += consumed;
                        state.inflate.set_dictionary(d).map_err(|e| {
                            error::new_err(format!("setting dictionary failed: {:?}", e))
                        })?;
                        continue;
                    }
                    return Err(error::new_err(
                        "preset dictionary required to decompress, but none was provided",
                    ));
                }
                Err(e) => {
                    return Err(error::new_err(format!(
                        "Error while decompressing data: {:?}",
                        e
                    )))
                }
            };
            let consumed = (state.inflate.total_in() - old_total_in) as usize;
            let produced = (state.inflate.total_out() - old_total_out) as usize;
            input_pos += consumed;
            output.extend_from_slice(&state.buf[..produced]);

            if matches!(status, Status::StreamEnd) {
                state.eof = true;
                if input_pos < input.len() {
                    state.unused_data.extend_from_slice(&input[input_pos..]);
                }
                break;
            }
            if consumed == 0 && produced == 0 {
                // No forward progress with current input — done for now.
                break;
            }
            if input_pos >= input.len() && max_length == 0 {
                // All input consumed, unlimited mode — done.
                break;
            }
            // Grow buffer if we filled it and have more input to feed.
            if produced == want && max_length == 0 {
                state.buf.resize(state.buf.len() * 2, 0);
            }
        }
        state.needs_input = input_pos == input.len() && !state.eof;
        Ok(PyBytes::new(py, &output).unbind())
    }

    #[pyo3(signature = (length=16384, /))]
    fn flush(&self, py: Python<'_>, length: i64) -> PyResult<Py<PyBytes>> {
        if length <= 0 {
            return Err(PyValueError::new_err("length must be greater than zero"));
        }
        // `length` is a working-buffer hint per CPython spec — flush must
        // drain ALL remaining output, not stop at `length` bytes. Cap the
        // scratch buffer (callers can pass sys.maxsize); we'll loop until
        // the decoder reports StreamEnd or stalls.
        const MAX_FLUSH_BUF: usize = 65536;
        let buf_size = (length as usize).min(MAX_FLUSH_BUF).max(1024);
        let mut guard = self.state.lock().unwrap();
        let state = &mut *guard;
        if state.eof {
            return Ok(PyBytes::new(py, b"").unbind());
        }
        if state.buf.len() < buf_size {
            state.buf.resize(buf_size, 0);
        }
        // Feed unconsumed tail with Finish, drain pending output.
        let mut input: Vec<u8> = std::mem::take(&mut state.unconsumed_tail);
        let mut input_pos = 0;
        let mut output: Vec<u8> = Vec::new();
        loop {
            let chunk_in = &input[input_pos..];
            let old_total_in = state.inflate.total_in();
            let old_total_out = state.inflate.total_out();
            let result = state
                .inflate
                .decompress(chunk_in, &mut state.buf, InflateFlush::Finish);
            let consumed = (state.inflate.total_in() - old_total_in) as usize;
            let produced = (state.inflate.total_out() - old_total_out) as usize;
            input_pos += consumed;
            output.extend_from_slice(&state.buf[..produced]);
            match result {
                Ok(Status::StreamEnd) => {
                    state.eof = true;
                    break;
                }
                Ok(_) => {
                    if consumed == 0 && produced == 0 {
                        // No forward progress — stop.
                        break;
                    }
                    // Otherwise, loop and let the decoder emit more.
                }
                Err(e) => {
                    return Err(error::new_err(format!(
                        "Error while flushing: {:?}",
                        e
                    )));
                }
            }
            // Empty the input buffer once we've fed everything — subsequent
            // iters drain the decoder's internal state.
            if input_pos >= input.len() {
                input.clear();
                input_pos = 0;
            }
        }
        Ok(PyBytes::new(py, &output).unbind())
    }

    fn copy(&self) -> PyResult<Decompress> {
        Err(PyNotImplementedError::new_err(
            "Decompress.copy not yet supported — needs libz-rs-sys inflateCopy",
        ))
    }

    #[getter]
    fn unused_data(&self, py: Python<'_>) -> Py<PyBytes> {
        let state = self.state.lock().unwrap();
        PyBytes::new(py, &state.unused_data).unbind()
    }

    #[getter]
    fn unconsumed_tail(&self, py: Python<'_>) -> Py<PyBytes> {
        let state = self.state.lock().unwrap();
        PyBytes::new(py, &state.unconsumed_tail).unbind()
    }

    #[getter]
    fn eof(&self) -> bool {
        self.state.lock().unwrap().eof
    }

    #[getter]
    fn needs_input(&self) -> bool {
        self.state.lock().unwrap().needs_input
    }
}

// ---- module registration ----------------------------------------------------

#[pymodule]
fn zlib_py(m: &Bound<'_, PyModule>) -> PyResult<()> {
    let py = m.py();

    m.add("error", py.get_type::<error>())?;

    // Compression levels.
    m.add("Z_NO_COMPRESSION", 0i32)?;
    m.add("Z_BEST_SPEED", 1i32)?;
    m.add("Z_BEST_COMPRESSION", 9i32)?;
    m.add("Z_DEFAULT_COMPRESSION", -1i32)?;

    // Strategies.
    m.add("Z_FILTERED", 1i32)?;
    m.add("Z_HUFFMAN_ONLY", 2i32)?;
    m.add("Z_RLE", 3i32)?;
    m.add("Z_FIXED", 4i32)?;
    m.add("Z_DEFAULT_STRATEGY", 0i32)?;

    // Flush modes.
    m.add("Z_NO_FLUSH", 0i32)?;
    m.add("Z_PARTIAL_FLUSH", 1i32)?;
    m.add("Z_SYNC_FLUSH", 2i32)?;
    m.add("Z_FULL_FLUSH", 3i32)?;
    m.add("Z_FINISH", 4i32)?;
    m.add("Z_BLOCK", 5i32)?;
    m.add("Z_TREES", 6i32)?;

    // Misc.
    m.add("MAX_WBITS", 15i32)?;
    m.add("DEFLATED", 8i32)?;
    m.add("DEF_BUF_SIZE", 16384i32)?;
    m.add("DEF_MEM_LEVEL", 8i32)?;

    // Version strings (placeholders — we don't link libz).
    m.add("ZLIB_VERSION", "1.3.1.zlib-rs-0.6.3")?;
    m.add("ZLIB_RUNTIME_VERSION", "1.3.1.zlib-rs-0.6.3")?;

    m.add_class::<Compress>()?;
    m.add_class::<Decompress>()?;

    m.add_function(wrap_pyfunction!(adler32, m)?)?;
    m.add_function(wrap_pyfunction!(crc32, m)?)?;
    m.add_function(wrap_pyfunction!(adler32_combine, m)?)?;
    m.add_function(wrap_pyfunction!(crc32_combine, m)?)?;
    m.add_function(wrap_pyfunction!(compress, m)?)?;
    m.add_function(wrap_pyfunction!(decompress, m)?)?;
    m.add_function(wrap_pyfunction!(compressobj, m)?)?;
    m.add_function(wrap_pyfunction!(decompressobj, m)?)?;

    Ok(())
}
