"""
SameBoy — Game Boy and Game Boy Color emulator.

Accurate Game Boy, Game Boy Color, and Super Game Boy emulator with
an SDL2 frontend for Linux. Includes compiled boot ROMs and shaders.

Requires building rgbds and cppp from source as build-time tools
(these are NOT installed, only used during compilation).

Source: https://github.com/LIJI32/SameBoy
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from core.package_base import PackageBase


class SameBoy(PackageBase):
    name = "sameboy"
    display_name = "SameBoy"
    version = "latest"
    version_type = "git_latest"
    source_url = "https://github.com/LIJI32/SameBoy.git"
    homepage = "https://sameboy.github.io"
    description = "Accurate Game Boy, Game Boy Color, and Super Game Boy emulator"

    apt_build_deps = [
        "git",
        "build-essential",
        "pkg-config",
        "bison",
        "libsdl2-dev",
        "libpng-dev",
        "libgl-dev",
        "libgdk-pixbuf-2.0-dev",
        "libglib2.0-dev",
    ]

    def get_effective_version(self) -> str:
        """SameBoy uses vX.Y.Z tags (sometimes vX.Y without patch)."""
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
                    # Match vX.Y or vX.Y.Z, skip -libretro tags
                    if tag.startswith("v") and "-" not in tag:
                        ver = tag[1:]
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

# ── Find latest release tag ──────────────────────────────────────────
# Tags: v1.0, v1.0.1, v1.0.2 — skip -libretro suffixed tags
step "Finding latest SameBoy release tag..."

LATEST_VER=$(git ls-remote --tags "$REPO_URL" \\
    | grep -v '\\^{{}}' \\
    | sed 's|.*refs/tags/||' \\
    | grep -E '^v[0-9]+\\.[0-9]+(\\.[0-9]+)?$' \\
    | sed 's/^v//' \\
    | sort -V \\
    | tail -1)

if [ -z "$LATEST_VER" ]; then
    die "Could not determine latest SameBoy release tag"
fi

VERSION="$LATEST_VER"
GIT_TAG="v$VERSION"
ok "Latest tag: $GIT_TAG  →  version: $VERSION"

# ── Build rgbds (boot ROM assembler) ─────────────────────────────────
# rgbds is not packaged in Debian, must be built from source.
# Only used at build time to compile boot ROMs from assembly.
step "Building rgbds (Game Boy assembler)..."
rm -rf rgbds
git clone --depth 1 --branch v0.9.4 https://github.com/gbdev/rgbds.git rgbds
cd rgbds
make -j$(nproc)
RGBDS_DIR="$(pwd)"
export PATH="$RGBDS_DIR:$PATH"
cd "$BUILD_DIR"
ok "rgbds built: $(rgbasm --version)"

# ── Build cppp (C preprocessor tool) ─────────────────────────────────
step "Building cppp..."
rm -rf cppp
git clone --depth 1 https://github.com/BR903/cppp.git cppp
cd cppp
make -j$(nproc)
export PATH="$(pwd):$PATH"
cd "$BUILD_DIR"
ok "cppp built"

# ── Clone SameBoy ────────────────────────────────────────────────────
step "Cloning SameBoy $GIT_TAG..."
rm -rf SameBoy
git clone --depth 1 --branch "$GIT_TAG" "$REPO_URL" SameBoy
cd SameBoy

# ── Build SDL frontend ───────────────────────────────────────────────
step "Building SameBoy SDL frontend..."
make -j$(nproc) sdl CONF=native_release

# ── Stage into DESTDIR ────────────────────────────────────────────────
step "Staging install..."
STAGING=$(mktemp -d)
make install DESTDIR="$STAGING" PREFIX=/usr FREEDESKTOP=true

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
Depends: libsdl2-2.0-0, libpng16-16t64 | libpng16-16, libgl1
Homepage: {self.homepage}
Description: {self.description}
 Includes SDL2 frontend, boot ROMs, shaders, palettes, and desktop integration.
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
