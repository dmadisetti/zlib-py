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

        # Custom CPython: take a current nixpkgs python derivation as scaffolding
        # (we only reuse its configure/build wiring), swap the source for our
        # pinned git rev, and add autoreconfHook so the missing ./configure is
        # regenerated before nixpkgs' configurePhase runs.
        #
        # The base attribute (`python313`) is just the scaffold — the resulting
        # interpreter's actual version comes from the cpython commit. If the
        # commit lives on a different branch, swap the scaffold accordingly.
        cpythonShortRev = builtins.substring 0 7 cpythonRev;
        customPython = pkgs.python313.overrideAttrs (old: {
          pname = "cpython-git";
          version = cpythonShortRev;
          src = cpythonSrc;
          nativeBuildInputs = (old.nativeBuildInputs or [])
            ++ [ pkgs.autoreconfHook ];
          doCheck = false;
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

        zlibPy = customPython.pkgs.buildPythonPackage {
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

          postPatch = ''
            chmod -R u+w .
            sed "s|@PYO3_SRC@|${pyo3Src}|g" \
              ${cargoVendor}/Cargo.toml.patched > Cargo.toml
            cp ${cargoVendor}/Cargo.lock Cargo.lock
            mkdir -p .cargo
            sed "s|@VENDOR_DIR@|${cargoVendor}/vendor|g" \
              ${cargoVendor}/config.toml > .cargo/config.toml
          '';
        };

        testEnv = customPython.withPackages (ps: [ zlibPy ps.pytest ]);

      in {
        packages = {
          default = zlibPy;
          python  = customPython.withPackages (_: [ zlibPy ]);
          inherit testEnv;
        };

        devShells.default = pkgs.mkShell {
          packages = [
            customPython
            customPython.pkgs.pytest
            pkgs.maturin
            pkgs.cargo
            pkgs.rustc
          ];
        };
      });
}
