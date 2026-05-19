{
  description = "zlib-py — pyo3 cdylib built against a pinned CPython rev and a pinned pyo3 rev";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        lib = pkgs.lib;

        cpythonRev = "5775aa8e295102156de14fd1ba284722c6ede95a";
        pyo3Rev    = "6d0c1ee1923faa26b95c652d7947d1927a5c86ae";

        cpythonSrc = pkgs.fetchFromGitHub {
          owner  = "python";
          repo   = "cpython";
          rev    = cpythonRev;
          sha256 = "sha256-QtzHQqVUHzTyO9WzlNSz2tZ+Pab82nxPOn6E2RrudSo=";
        };

        # pyo3 source fetched outside the FOD so we can use path patches —
        # path patches don't trip --offline the way git patches do, even
        # after vendoring.
        pyo3Src = pkgs.fetchFromGitHub {
          owner  = "PyO3";
          repo   = "pyo3";
          rev    = pyo3Rev;
          sha256 = "sha256-nbOwTSb3MTICxi0d8nIlMOp2htfAkOLfNnzT2u2TK4k=";
        };

        # Custom CPython: take a current nixpkgs python derivation as
        # scaffolding (we only reuse its configure/build wiring) and swap the
        # source for our pinned git rev. The tarball-shaped source from
        # fetchFromGitHub already contains a pregenerated `./configure`, so
        # there's no need for autoreconfHook here.
        #
        # Two-stage override:
        #   1. `.override { self = customPython; ... }` re-runs the python
        #      derivation function with `self` bound to *our* final
        #      derivation. This is the fix-point that makes passthru attrs
        #      (`pkgs`, `withPackages`, `pythonForBuild`) reference the
        #      customized interpreter rather than the unmodified scaffold.
        #   2. `.overrideAttrs` then swaps `src` / `version` on top. Passthru
        #      is already wired to `self`, so withPackages picks up the
        #      overridden interpreter correctly.
        #
        # Plain `.overrideAttrs` alone leaves passthru pinned to the original
        # python — `customPython.withPackages` silently builds a stock env.
        #
        # The base attribute (`python315`) determines the build *scaffolding*
        # (configure flags, library deps); the actual interpreter version
        # comes from the cpython commit. Pick a scaffold close to the target
        # version so configure flags match.
        cpythonShortRev = builtins.substring 0 7 cpythonRev;
        customPython = (pkgs.python315.override (old: {
          self = customPython;
          # Tell nixpkgs what version we're *actually* building so installed
          # paths (lib/python3.16/...) line up with what cpython 3.16-alpha
          # writes. Without this nixpkgs computes paths against the scaffold
          # version (3.15) and postInstall steps like stripTests fail when
          # they can't find lib/python3.15/test/__init__.py.
          sourceVersion = {
            major = "3";
            minor = "16";
            patch = "0";
            suffix = "a-${cpythonShortRev}";
          };
          # Cross-compile passthru looks up `pkgsBuildTarget.${pythonAttr}`.
          # nixpkgs has no `python316` attribute yet, so pin to the closest
          # one (`python315`) for that lookup. Build-host side only — the
          # actual interpreter is still our overridden 3.16 derivation.
          pythonAttr = "python315";
          # Unused (src is overridden below) but the scaffold function
          # demands a non-null hash arg.
          hash = pkgs.lib.fakeHash;
        })).overrideAttrs (old: {
          pname = "cpython-git";
          version = cpythonShortRev;
          src = cpythonSrc;
          doCheck = false;

          # nixpkgs' preConfigure does a `substituteInPlace configure
          # --replace-fail 'libmpdec_machine=universal' …` to defeat Darwin
          # universal-build autodetection. CPython 3.16+ rewrote the
          # detection and the literal string is gone, so --replace-fail
          # aborts the build. Patch our copy to use --replace-quiet, which
          # tolerates a missing pattern; `export PYTHON_DECIMAL_WITH_MACHINE`
          # earlier in the same script still does the heavy lifting.
          preConfigure = builtins.replaceStrings
            [ "--replace-fail 'libmpdec_machine=universal'" ]
            [ "--replace-quiet 'libmpdec_machine=universal'" ]
            (old.preConfigure or "");

          # Bumping sourceVersion to 3.16 makes nixpkgs look for patches
          # under cpython/3.16/, which doesn't exist. The 3.15 patches
          # (no-ldconfig, virtualenv-permissions, mimetypes) apply cleanly
          # to 3.16-alpha, so re-pin to them.
          patches = pkgs.python315.drvAttrs.patches;
        });

        # Two flavours of the same [patch.crates-io] block:
        #   - realPatch uses absolute store paths, only used inside the FOD
        #     so cargo can resolve the patches when generating the lockfile.
        #   - placeholderPatch uses @PYO3_SRC@ tokens, written to the FOD's
        #     $out so the FOD never references another store path (which
        #     fixed-output derivations forbid). The consumer rewrites the
        #     tokens to the real pyo3 store path at build time.
        mkPatchBlock = pathPrefix: ''

          [patch.crates-io]
          pyo3                = { path = "${pathPrefix}" }
          pyo3-build-config   = { path = "${pathPrefix}/pyo3-build-config" }
          pyo3-ffi            = { path = "${pathPrefix}/pyo3-ffi" }
          pyo3-macros         = { path = "${pathPrefix}/pyo3-macros" }
          pyo3-macros-backend = { path = "${pathPrefix}/pyo3-macros-backend" }
        '';
        realPatch        = mkPatchBlock "${pyo3Src}";
        placeholderPatch = mkPatchBlock "@PYO3_SRC@";

        # Fixed-output derivation: produces vendor/ for the crates.io deps,
        # the cargo source-replacement config, and a regenerated Cargo.lock.
        # pyo3 itself is not vendored — it stays as a path patch resolved
        # against ${pyo3Src} at consumer time.
        cargoVendor = pkgs.stdenvNoCC.mkDerivation {
          name = "zlib-py-cargo-vendor";
          src = lib.cleanSource ./.;
          nativeBuildInputs = [ pkgs.cargo pkgs.git pkgs.cacert ];
          SSL_CERT_FILE = "${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt";
          buildPhase = ''
            runHook preBuild
            chmod -R u+w .
            cp Cargo.toml Cargo.toml.orig
            cat >> Cargo.toml <<PATCH
${realPatch}
PATCH
            export CARGO_HOME="$(mktemp -d)"
            cargo generate-lockfile
            mkdir -p "$out"
            cargo vendor "$out/vendor" \
              | sed "s|$out/vendor|@VENDOR_DIR@|g" \
              > "$out/config.toml"
            cp Cargo.lock "$out/Cargo.lock"
            # Write the placeholder-patched Cargo.toml for the consumer.
            cp Cargo.toml.orig "$out/Cargo.toml.patched"
            cat >> "$out/Cargo.toml.patched" <<PATCH
${placeholderPatch}
PATCH
            runHook postBuild
          '';
          dontInstall = true;
          dontFixup = true;
          outputHashAlgo = "sha256";
          outputHashMode = "recursive";
          outputHash = "sha256-cCAN6Wekbg1XS/cmWya2SqFi7uUZODWcU3vCvAIDS8M=";
        };

        # The package is built using the *scaffold* python's pkgs scope
        # rather than `customPython.pkgs`. customPython is 3.16-alpha and
        # nixpkgs has no python316 bootstrap chain — buildPythonPackage's
        # hooks (pythonRuntimeDepsCheckHook, etc.) import 3.15-built
        # `packaging`, which 3.16 can't load. Since we enabled pyo3's
        # `abi3-py38` feature, the resulting wheel's .so is version
        # agnostic, so customPython picks it up fine at runtime via
        # PYTHONPATH.
        scaffoldPython = pkgs.python315;
        zlibPy = scaffoldPython.pkgs.buildPythonPackage {
          pname = "zlib-py";
          version = "0.1.0";
          src = lib.cleanSource ./.;
          pyproject = true;

          nativeBuildInputs = with pkgs; [
            rustPlatform.maturinBuildHook
            cargo
            rustc
            maturin
          ];

          # pyo3 0.27 only knows up to Python 3.14; the scaffold here is
          # 3.15. With abi3-py38 enabled the actual ABI is stable, so the
          # check is overly conservative — wave it off.
          env.PYO3_USE_ABI3_FORWARD_COMPATIBILITY = "1";

          postPatch = ''
            chmod -R u+w .
            sed "s|@PYO3_SRC@|${pyo3Src}|g" \
              ${cargoVendor}/Cargo.toml.patched > Cargo.toml
            cp ${cargoVendor}/Cargo.lock Cargo.lock
            mkdir -p .cargo
            sed "s|@VENDOR_DIR@|${cargoVendor}/vendor|g" \
              ${cargoVendor}/config.toml > .cargo/config.toml
          '';

          # pyo3's abi3-py38 feature produces stable-ABI bindings, but
          # maturin still tags the .so with the build python's version
          # (`cpython-315-darwin.so`). Rename to `*.abi3.so` so any
          # 3.8+ interpreter — including customPython 3.16 — will load
          # it via the abi3 importer.
          postFixup = ''
            find $out -name "*.cpython-*-*.so" | while read -r f; do
              dir=$(dirname "$f")
              base=$(basename "$f" | sed 's/\.cpython-.*$/.abi3.so/')
              mv "$f" "$dir/$base"
            done
          '';
        };

        # Wrap customPython so the abi3 wheel built against the scaffold
        # python is importable by our 3.16-alpha interpreter.
        zlibPySitePackages = "${zlibPy}/${scaffoldPython.sitePackages}";
        mkCustomPythonEnv = extraPath: pkgs.runCommand "cpython-git-${cpythonShortRev}-env" {
          nativeBuildInputs = [ pkgs.makeWrapper ];
        } ''
          mkdir -p $out/bin
          for bin in ${customPython}/bin/python*; do
            name=$(basename $bin)
            makeWrapper $bin $out/bin/$name \
              --prefix PYTHONPATH : "${zlibPySitePackages}${extraPath}"
          done
        '';

        # A scaffold env that has pytest + all of its propagated deps
        # (pluggy, iniconfig, etc.) on a single site-packages tree. We
        # point our wrapper's PYTHONPATH at that tree so customPython can
        # `-m pytest` cleanly.
        pytestScaffold = scaffoldPython.withPackages (ps: [ ps.pytest ]);
        testEnv = mkCustomPythonEnv ":${pytestScaffold}/${scaffoldPython.sitePackages}";

      in {
        packages = {
          default = zlibPy;
          python  = mkCustomPythonEnv "";
          inherit testEnv;
        };

        devShells.default = pkgs.mkShell {
          packages = [
            customPython
            scaffoldPython.pkgs.pytest
            pkgs.maturin
            pkgs.cargo
            pkgs.rustc
          ];
        };
      });
}
