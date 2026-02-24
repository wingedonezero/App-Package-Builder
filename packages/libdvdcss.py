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

LATEST_TAG=$(git ls-remote --tags "$REPO_URL" \\
    | grep -v '\\^{{}}' \\
    | sed 's|.*refs/tags/||' \\
    | awk '{{
        tag = $0
        norm = tag
        sub(/^v/, "", norm)      # strip leading v
        gsub(/_/, ".", norm)     # underscores to dots
        print norm "\\t" tag      # normalised version TAB original tag
    }}' \\
    | sort -V -k1,1 \\
    | tail -1 \\
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

# ── Stage into DESTDIR ─────────────────────────────────────────────────
# checkinstall doesn't work reliably with meson's Python-based installer,
# so we stage with DESTDIR ourselves and package with dpkg-deb directly.
step "Staging install (DESTDIR)..."
STAGING=$(mktemp -d)
DESTDIR="$STAGING" ninja -C build install

# ── Write DEBIAN/control ───────────────────────────────────────────────
step "Writing package metadata..."
ARCH=$(dpkg --print-architecture)
mkdir -p "$STAGING/DEBIAN"
cat > "$STAGING/DEBIAN/control" <<CTRL
Package: {self.name}
Version: $VERSION
Architecture: $ARCH
Maintainer: App-Package-Builder <local>
Section: libs
Priority: optional
Homepage: {self.homepage}
Description: {self.description}
CTRL

# ── Build .deb ─────────────────────────────────────────────────────────
step "Building .deb with dpkg-deb..."
DEB_FILE="$OUTPUT_DIR/{self.name}_${{VERSION}}_${{ARCH}}.deb"
dpkg-deb --build "$STAGING" "$DEB_FILE"
rm -rf "$STAGING"
ok "Built: $DEB_FILE"
""" + self._script_footer()

        script_path.write_text(script)
        return script_path
