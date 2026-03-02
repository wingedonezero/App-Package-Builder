"""
SameBoy — Game Boy and Game Boy Color emulator (release).

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


# Shared build logic used by both release and master packages.
SAMEBOY_BUILD_DEPS = [
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


def _sameboy_build_and_stage() -> str:
    """Return the shared shell snippet that builds rgbds, cppp, SameBoy,
    and stages files into $STAGING.  Caller must set STAGING beforehand."""
    return r"""
# ── Build rgbds (boot ROM assembler) ─────────────────────────────────
# rgbds is not packaged in Debian, must be built from source.
# Only used at build time to compile boot ROMs from assembly.
step "Building rgbds (Game Boy assembler)..."
rm -rf rgbds
git clone --depth 1 --branch v0.9.4 https://github.com/gbdev/rgbds.git rgbds
cd rgbds
make -j$(nproc)
export PATH="$(pwd):$PATH"
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

cd SameBoy

# ── Build SDL frontend ───────────────────────────────────────────────
step "Building SameBoy SDL frontend..."
make -j$(nproc) sdl CONF=release

# ── Stage manually ───────────────────────────────────────────────────
# We stage files ourselves instead of 'make install' because the install
# target tries to build the XDG thumbnailer, which fails due to LTO
# object incompatibility with the SDL build.
step "Staging install..."
BINDIR="$STAGING/usr/bin"
DATADIR="$STAGING/usr/share/sameboy"
APPDIR="$STAGING/usr/share/applications"
MIMEDIR="$STAGING/usr/share/mime/packages"

mkdir -p "$BINDIR" "$DATADIR" "$APPDIR"

# Main binary
install -m 755 build/bin/SDL/sameboy "$BINDIR/"

# Data files (shaders, palettes, boot ROMs, etc.)
for item in Shaders Palettes BootROMs LICENSE registers.sym background.bmp; do
    if [ -e "build/bin/SDL/$item" ]; then
        cp -r "build/bin/SDL/$item" "$DATADIR/"
    fi
done
ok "Installed binary and data files"

# ── Desktop integration ──────────────────────────────────────────────
# Desktop file
if [ -f FreeDesktop/sameboy.desktop ]; then
    cp FreeDesktop/sameboy.desktop "$APPDIR/"
    ok "Installed desktop file"
fi

# MIME types
if [ -f FreeDesktop/sameboy.xml ]; then
    mkdir -p "$MIMEDIR"
    cp FreeDesktop/sameboy.xml "$MIMEDIR/"
    ok "Installed MIME types"
fi

# Icons (app + cartridge icons at all available sizes)
for size in 16 32 64 128 256 512; do
    ICON_DST="$STAGING/usr/share/icons/hicolor/${size}x${size}"

    # App icon
    for src in "FreeDesktop/AppIcon/${size}x${size}.png" \
               "FreeDesktop/${size}x${size}/apps/sameboy.png"; do
        if [ -f "$src" ]; then
            mkdir -p "$ICON_DST/apps"
            cp "$src" "$ICON_DST/apps/sameboy.png"
            break
        fi
    done

    # Cartridge MIME icons
    for type in x-gameboy-rom x-gameboy-color-rom; do
        for src in "FreeDesktop/${size}x${size}/mimetypes/${type}.png"; do
            if [ -f "$src" ]; then
                mkdir -p "$ICON_DST/mimetypes"
                cp "$src" "$ICON_DST/mimetypes/${type}.png"
            fi
        done
    done
done
ok "Installed icons"

cd "$BUILD_DIR"
"""


class SameBoy(PackageBase):
    name = "sameboy"
    display_name = "SameBoy"
    version = "latest"
    version_type = "git_latest"
    source_url = "https://github.com/LIJI32/SameBoy.git"
    homepage = "https://sameboy.github.io"
    description = "Accurate Game Boy, Game Boy Color, and Super Game Boy emulator"

    apt_build_deps = list(SAMEBOY_BUILD_DEPS)

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

# ── Clone at that tag ────────────────────────────────────────────────
step "Cloning SameBoy $GIT_TAG..."
rm -rf SameBoy
git clone --depth 1 --branch "$GIT_TAG" "$REPO_URL" SameBoy

STAGING=$(mktemp -d)
""" + _sameboy_build_and_stage() + f"""
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
