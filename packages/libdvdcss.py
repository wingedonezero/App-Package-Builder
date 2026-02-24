"""
libdvdcss — DVD CSS decryption library.

Previously available via deb-multimedia, now built from source.
Source: https://code.videolan.org/videolan/libdvdcss
"""

from __future__ import annotations

from pathlib import Path

from core.package_base import PackageBase


class LibDvdCss(PackageBase):
    name = "libdvdcss"
    display_name = "libdvdcss"
    version = "latest"
    version_type = "git_latest"
    source_url = "https://code.videolan.org/videolan/libdvdcss.git"
    homepage = "https://www.videolan.org/developers/libdvdcss.html"
    description = "Simple library designed for accessing DVDs like a block device without having to bother about the decryption"

    apt_build_deps = [
        "git",
        "meson",
        "ninja-build",
        "gcc",
        "checkinstall",
        "pkg-config",
    ]

    def write_build_script(self, build_dir: Path, output_dir: Path) -> Path:
        script_path = build_dir / "build.sh"

        script = self._script_header() + f"""
BUILD_DIR="{build_dir}"
OUTPUT_DIR="{output_dir}"
REPO_URL="{self.source_url}"

cd "$BUILD_DIR"

# ── Find latest tag ────────────────────────────────────────────────────
# Note: repo has mixed tag naming — old style: v1_2_8, new style: 1.5.0
# We normalise all tags to dotted form, version-sort them, then map back
step "Finding latest release tag..."

LATEST_TAG=$(git ls-remote --tags "$REPO_URL" \
    | grep -v '\^{{}}' \
    | sed 's|.*refs/tags/||' \
    | awk '{{
        tag = $0
        norm = tag
        sub(/^v/, "", norm)      # strip leading v
        gsub(/_/, ".", norm)     # underscores to dots
        print norm "\t" tag      # normalised version TAB original tag
    }}' \
    | sort -V -k1,1 \
    | tail -1 \
    | cut -f2)

if [ -z "$LATEST_TAG" ]; then
    die "Could not determine latest tag from $REPO_URL"
fi

# Derive clean version number from the tag
VERSION="$LATEST_TAG"
VERSION="${{VERSION#v}}"        # strip leading v if present
VERSION=$(echo "$VERSION" | tr '_' '.')  # underscores to dots
ok "Latest tag: $LATEST_TAG  →  version: $VERSION"

# ── Clone at that exact tag ────────────────────────────────────────────
step "Cloning libdvdcss $LATEST_TAG..."
rm -rf libdvdcss
git clone --depth 1 --branch "$LATEST_TAG" "$REPO_URL" libdvdcss
cd libdvdcss

# ── Build ──────────────────────────────────────────────────────────────
step "Configuring with meson..."
meson setup build --prefix=/usr --buildtype=release

step "Building..."
ninja -C build

# ── Package ────────────────────────────────────────────────────────────
step "Creating .deb with checkinstall..."

# checkinstall --install=no: build the .deb, don't install it
cd build
sudo checkinstall \\
    --install=no \\
    --pkgname="{self.name}" \\
    --pkgversion="$VERSION" \\
    --pkgrelease=1 \\
    --pkglicense="LGPL-2.1" \\
    --pkggroup="libs" \\
    --pkgsource="{self.source_url}" \\
    --pakdir="$BUILD_DIR/libdvdcss/build" \\
    --nodoc \\
    --default \\
    ninja install

# ── Move .deb to output dir ────────────────────────────────────────────
step "Moving .deb to output directory..."
DEB=$(find "$BUILD_DIR/libdvdcss/build" -maxdepth 1 -name "*.deb" | head -1)

if [ -z "$DEB" ]; then
    die "No .deb file found after checkinstall!"
fi

mv "$DEB" "$OUTPUT_DIR/"
ok "Built: $OUTPUT_DIR/$(basename "$DEB")"
""" + self._script_footer()

        script_path.write_text(script)
        return script_path
