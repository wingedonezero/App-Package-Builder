"""
ares — multi-system emulator focused on accuracy and preservation.

Supports Nintendo, Sega, NEC, SNK, and many more systems.
Install librashader first for GPU shader support (loaded at runtime).

Source: https://github.com/ares-emulator/ares
"""

from __future__ import annotations

from pathlib import Path

from core.package_base import PackageBase


class Ares(PackageBase):
    name = "ares"
    display_name = "ares"
    version = "latest"
    version_type = "git_latest"
    source_url = "https://github.com/ares-emulator/ares.git"
    homepage = "https://ares-emu.net"
    description = "Multi-system emulator focused on accuracy and preservation"

    apt_build_deps = [
        "git",
        "cmake",
        "ninja-build",
        "g++",
        "pkg-config",
        "libgtk-3-dev",
        "libgl-dev",
        "libasound2-dev",
        "libpulse-dev",
        "libudev-dev",
        "libopenal-dev",
        "libao-dev",
        "libsdl3-dev",
    ]

    def write_build_script(self, build_dir: Path, output_dir: Path) -> Path:
        script_path = build_dir / "build.sh"

        script = self._script_header() + f"""
BUILD_DIR="{build_dir}"
OUTPUT_DIR="{output_dir}"
REPO_URL="{self.source_url}"

cd "$BUILD_DIR"

# ── Find latest vNNN tag ──────────────────────────────────────────────
step "Finding latest ares release tag..."

LATEST_TAG=$(git ls-remote --tags "$REPO_URL" \\
    | grep -v '\\^{{}}' \\
    | sed 's|.*refs/tags/||' \\
    | grep -E '^v[0-9]+$' \\
    | sed 's/^v//' \\
    | sort -n \\
    | tail -1)

if [ -z "$LATEST_TAG" ]; then
    die "Could not determine latest ares release tag"
fi

VERSION="$LATEST_TAG"
GIT_TAG="v$VERSION"
ok "Latest tag: $GIT_TAG  →  version: $VERSION"

# ── Clone at that tag ─────────────────────────────────────────────────
step "Cloning ares $GIT_TAG..."
rm -rf ares
git clone --depth 1 --branch "$GIT_TAG" "$REPO_URL" ares
cd ares

# ── Configure with CMake ──────────────────────────────────────────────
step "Configuring with cmake..."
cmake -B build -G Ninja \\
    -DCMAKE_BUILD_TYPE=Release \\
    -DCMAKE_INSTALL_PREFIX=/usr \\
    -DARES_BUILD_LOCAL=ON \\
    -DARES_SKIP_DEPS=ON \\
    -DARES_ENABLE_LIBRASHADER=ON \\
    -DARES_BUNDLE_SHADERS=OFF

# ── Build ─────────────────────────────────────────────────────────────
step "Building ares (this may take a while)..."
ninja -C build

# ── Stage into DESTDIR ────────────────────────────────────────────────
step "Staging install..."
STAGING=$(mktemp -d)
DESTDIR="$STAGING" cmake --install build

# ── Write DEBIAN/control ─────────────────────────────────────────────
step "Writing package metadata..."
ARCH=$(dpkg --print-architecture)
mkdir -p "$STAGING/DEBIAN"
cat > "$STAGING/DEBIAN/control" <<CTRL
Package: {self.name}
Version: $VERSION
Architecture: $ARCH
Maintainer: App-Package-Builder <local>
Section: games
Priority: optional
Homepage: {self.homepage}
Description: {self.description}
 Install librashader for GPU shader support (optional, loaded at runtime).
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
