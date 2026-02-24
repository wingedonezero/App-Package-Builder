"""
vapoursynth-ffms2 — FFmpegSource2 rebuilt with VapourSynth plugin support.

Debian's libffms2-5 is built without VapourSynth support. This builds
ffms2 from source (the VS plugin code is compiled directly into libffms2.so),
then adds a symlink in the VS autoload directory so VapourSynth can find it.

Conflicts with and replaces Debian's libffms2-5 and libffms2-dev.
Uninstall those first:
    sudo apt remove libffms2-5 libffms2-dev

Source: https://github.com/FFMS/ffms2
"""

from __future__ import annotations

from pathlib import Path

from core.package_base import PackageBase


class VapourSynthFfms2(PackageBase):
    name = "vapoursynth-ffms2"
    display_name = "vapoursynth-ffms2"
    version = "latest"
    version_type = "git_latest"
    source_url = "https://github.com/FFMS/ffms2.git"
    homepage = "https://github.com/FFMS/ffms2"
    description = "FFmpegSource2 library rebuilt with VapourSynth plugin support"

    apt_build_deps = [
        "git",
        "autoconf",
        "automake",
        "libtool",
        "pkg-config",
        "libavformat-dev",
        "libavcodec-dev",
        "libavutil-dev",
        "libswscale-dev",
        "libswresample-dev",
        "zlib1g-dev",
    ]

    def write_build_script(self, build_dir: Path, output_dir: Path) -> Path:
        script_path = build_dir / "build.sh"

        script = self._script_header() + f"""
BUILD_DIR="{build_dir}"
OUTPUT_DIR="{output_dir}"
REPO_URL="{self.source_url}"

cd "$BUILD_DIR"

# ── Find latest tag ────────────────────────────────────────────────────
step "Finding latest ffms2 release tag..."

LATEST_TAG=$(git ls-remote --tags "$REPO_URL" \\
    | grep -v '\\^{{}}' \\
    | sed 's|.*refs/tags/||' \\
    | grep -E '^v?[0-9]' \\
    | awk '{{tag=$0; norm=tag; sub(/^v/,"",norm); print norm"\\t"tag}}' \\
    | sort -V -k1,1 \\
    | tail -1 \\
    | cut -f2)

if [ -z "$LATEST_TAG" ]; then
    die "Could not determine latest ffms2 release tag"
fi

VERSION="${{LATEST_TAG#v}}"
ok "Latest tag: $LATEST_TAG  →  version: $VERSION"

# ── Clone ──────────────────────────────────────────────────────────────
step "Cloning ffms2 $LATEST_TAG..."
rm -rf ffms2
git clone --depth 1 --branch "$LATEST_TAG" "$REPO_URL" ffms2
cd ffms2

# ── Build with autotools ───────────────────────────────────────────────
# Note: VapourSynth plugin code lives in src/vapoursynth/ and is compiled
# directly into libffms2.so — no separate configure flag needed, the VS
# headers are bundled in the repo.
step "Running autogen.sh..."
./autogen.sh

step "Configuring..."
./configure --prefix=/usr --disable-static

step "Building..."
make -j$(nproc)

# ── Stage into DESTDIR ─────────────────────────────────────────────────
step "Staging install (DESTDIR)..."
STAGING=$(mktemp -d)
DESTDIR="$STAGING" make install

# ── Add VapourSynth plugin autoload symlink ────────────────────────────
# VS plugin autoloader scans its plugin dir for .so files that export
# VapourSynthPluginInit2. libffms2.so exports it, so we symlink it in.
step "Adding VapourSynth plugin symlink..."
VSDIR="$STAGING/usr/lib/x86_64-linux-gnu/vapoursynth"
mkdir -p "$VSDIR"

# Find the versioned .so that was installed
VERSIONED_SO=$(find "$STAGING/usr/lib" -maxdepth 3 -name "libffms2.so.*.*" | head -1)
if [ -z "$VERSIONED_SO" ]; then
    die "Could not find installed libffms2.so after make install"
fi
SO_NAME=$(basename "$VERSIONED_SO")
ok "Found: $SO_NAME"

# Relative symlink from vapoursynth/ up one level to the library
ln -sf "../$SO_NAME" "$VSDIR/libffms2.so"
ok "Symlinked: $VSDIR/libffms2.so → ../$SO_NAME"

# ── Write DEBIAN/control ───────────────────────────────────────────────
step "Writing package metadata..."
ARCH=$(dpkg --print-architecture)
mkdir -p "$STAGING/DEBIAN"
cat > "$STAGING/DEBIAN/control" <<CTRL
Package: {self.name}
Version: $VERSION
Architecture: $ARCH
Maintainer: App-Package-Builder <local>
Section: video
Priority: optional
Depends: vapoursynth
Conflicts: libffms2-5, libffms2-dev
Replaces: libffms2-5, libffms2-dev
Provides: libffms2-5, libffms2-dev
Homepage: {self.homepage}
Description: {self.description}
CTRL

# ── Build .deb ─────────────────────────────────────────────────────────
step "Building .deb with dpkg-deb..."
DEB_FILE="$OUTPUT_DIR/{self.name}_${{VERSION}}_${{ARCH}}.deb"
dpkg-deb --build "$STAGING" "$DEB_FILE"
rm -rf "$STAGING"
ok "Built: $DEB_FILE"

echo ""
ok "IMPORTANT: Before installing, remove Debian's version:"
echo "  sudo apt remove libffms2-5 libffms2-dev"
echo "  sudo dpkg -i $DEB_FILE"
""" + self._script_footer()

        script_path.write_text(script)
        return script_path
