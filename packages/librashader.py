"""
librashader — RetroArch shader runtime library.

Provides the librashader shared library, static library, headers, and
pkg-config file.  Used by ares and other emulators for GPU shader support.

Source: https://github.com/SnowflakePowered/librashader
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from core.package_base import PackageBase


class Librashader(PackageBase):
    name = "librashader"
    display_name = "librashader"
    version = "latest"
    version_type = "git_latest"
    source_url = "https://github.com/SnowflakePowered/librashader.git"
    homepage = "https://github.com/SnowflakePowered/librashader"
    description = "RetroArch shaders for all — GPU shader runtime library"

    apt_build_deps = [
        "git",
        "rustc",
        "cargo",
        "gcc",
        "g++",
        "patchelf",
        "pkg-config",
    ]

    def get_effective_version(self) -> str:
        """librashader uses librashader-vX.Y.Z tags."""
        try:
            result = subprocess.run(
                ["git", "ls-remote", "--tags", self.source_url],
                capture_output=True,
                text=True,
                timeout=10,
            )
            versions = []
            for line in result.stdout.splitlines():
                if "refs/tags/" in line and "^{}" not in line:
                    tag = line.split("refs/tags/")[-1].strip()
                    # Match only main release tags: librashader-v0.10.1
                    # Excludes crate-specific tags like librashader-capi-v0.10.1
                    if tag.startswith("librashader-v") and tag.count("-") == 1:
                        ver = tag[len("librashader-v"):]
                        versions.append(ver)
            if versions:

                def version_key(v: str) -> tuple:
                    try:
                        return tuple(int(x) for x in v.split("."))
                    except ValueError:
                        return (0,)

                versions.sort(key=version_key)
                return versions[-1]
        except Exception:
            pass
        return "latest"

    def write_build_script(self, build_dir: Path, output_dir: Path) -> Path:
        script_path = build_dir / "build.sh"

        script = self._script_header() + f"""
BUILD_DIR="{build_dir}"
OUTPUT_DIR="{output_dir}"
REPO_URL="{self.source_url}"

cd "$BUILD_DIR"

# ── Find latest librashader release tag ───────────────────────────────
# Tags are: librashader-v0.5.0, librashader-v0.10.1, etc.
# Exclude per-crate tags like librashader-capi-v0.10.1
step "Finding latest librashader release tag..."

LATEST_VER=$(git ls-remote --tags "$REPO_URL" \\
    | grep -v '\\^{{}}' \\
    | sed 's|.*refs/tags/||' \\
    | grep -E '^librashader-v[0-9]+\\.[0-9]+\\.[0-9]+$' \\
    | sed 's/^librashader-v//' \\
    | sort -V \\
    | tail -1)

if [ -z "$LATEST_VER" ]; then
    die "Could not determine latest librashader release tag"
fi

VERSION="$LATEST_VER"
GIT_TAG="librashader-v$VERSION"
ok "Latest tag: $GIT_TAG  →  version: $VERSION"

# ── Clone at that tag ─────────────────────────────────────────────────
step "Cloning librashader $GIT_TAG..."
rm -rf librashader
git clone --depth 1 --branch "$GIT_TAG" "$REPO_URL" librashader
cd librashader

# ── Build C shared library ────────────────────────────────────────────
# RUSTC_BOOTSTRAP=1 allows nightly features on stable rustc
step "Building librashader C API (this may take a while)..."
RUSTC_BOOTSTRAP=1 cargo run -p librashader-build-script -- --profile optimized

# ── Set SONAME ────────────────────────────────────────────────────────
step "Patching SONAME..."
patchelf --set-soname librashader.so.2 target/optimized/librashader.so
ok "SONAME set to librashader.so.2"

# ── Stage into DESTDIR ────────────────────────────────────────────────
step "Staging install..."
STAGING=$(mktemp -d)
ARCH=$(dpkg --print-architecture)
LIBDIR="$STAGING/usr/lib"
INCDIR="$STAGING/usr/include/librashader"
PCDIR="$STAGING/usr/lib/pkgconfig"

mkdir -p "$LIBDIR" "$INCDIR" "$PCDIR"

# Shared library + SONAME symlinks
cp target/optimized/librashader.so "$LIBDIR/librashader.so.$VERSION"
ln -sf "librashader.so.$VERSION" "$LIBDIR/librashader.so.2"
ln -sf "librashader.so.2" "$LIBDIR/librashader.so"

# Static library
cp target/optimized/librashader.a "$LIBDIR/librashader.a"

# Headers — prefer freshly generated header, fall back to bundled copy
if [ -f target/optimized/librashader.h ]; then
    cp target/optimized/librashader.h "$INCDIR/"
elif [ -f include/librashader.h ]; then
    cp include/librashader.h "$INCDIR/"
else
    die "Cannot find librashader.h"
fi
cp include/librashader_ld.h "$INCDIR/"
ok "Installed headers to $INCDIR"

# pkg-config file
cat > "$PCDIR/librashader.pc" <<PCEOF
prefix=/usr
exec_prefix=\\${{prefix}}
libdir=\\${{exec_prefix}}/lib
includedir=\\${{prefix}}/include/librashader

Name: librashader
Description: RetroArch shaders for all
Version: $VERSION
Libs: -L\\${{libdir}} -lrashader
Cflags: -I\\${{includedir}}
PCEOF
ok "Installed pkg-config file"

# ── ldconfig trigger ──────────────────────────────────────────────────
mkdir -p "$STAGING/DEBIAN"
cat > "$STAGING/DEBIAN/triggers" <<TRIGGERS
activate-noawait ldconfig
TRIGGERS

# ── Write DEBIAN/control ─────────────────────────────────────────────
step "Writing package metadata..."
cat > "$STAGING/DEBIAN/control" <<CTRL
Package: {self.name}
Version: $VERSION
Architecture: $ARCH
Maintainer: App-Package-Builder <local>
Section: libs
Priority: optional
Homepage: {self.homepage}
Description: {self.description}
 Includes shared library, static library, headers, and pkg-config file.
CTRL

# ── Build .deb ────────────────────────────────────────────────────────
step "Building .deb with dpkg-deb..."
DEB_FILE="$OUTPUT_DIR/{self.name}_${{VERSION}}_${{ARCH}}.deb"
dpkg-deb --root-owner-group --build "$STAGING" "$DEB_FILE"
rm -rf "$STAGING"
ok "Built: $DEB_FILE"
""" + self._script_footer()

        script_path.write_text(script)
        return script_path
