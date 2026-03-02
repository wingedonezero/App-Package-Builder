"""
SameBoy (master) — Game Boy and Game Boy Color emulator (development build).

Builds from the master branch for the latest features and fixes.
For the stable release build, see sameboy.py.

Source: https://github.com/LIJI32/SameBoy
"""

from __future__ import annotations

from pathlib import Path

from core.package_base import PackageBase
from packages.sameboy import SAMEBOY_BUILD_DEPS, _sameboy_build_and_stage


class SameBoyMaster(PackageBase):
    name = "sameboy-master"
    display_name = "SameBoy (master)"
    version = "master"
    version_type = "git_tag"
    source_url = "https://github.com/LIJI32/SameBoy.git"
    homepage = "https://sameboy.github.io"
    description = "Accurate Game Boy, Game Boy Color, and Super Game Boy emulator (master)"

    apt_build_deps = list(SAMEBOY_BUILD_DEPS)

    def write_build_script(self, build_dir: Path, output_dir: Path) -> Path:
        script_path = build_dir / "build.sh"

        script = self._script_header() + f"""
BUILD_DIR="{build_dir}"
OUTPUT_DIR="{output_dir}"
REPO_URL="{self.source_url}"

cd "$BUILD_DIR"

# ── Clone master ─────────────────────────────────────────────────────
step "Cloning SameBoy master..."
rm -rf SameBoy
git clone --depth 50 "$REPO_URL" SameBoy

# Derive a version from git describe (e.g. v1.0.2-15-gabcdef → 1.0.2+git15)
cd SameBoy
RAW=$(git describe --tags --abbrev=7 2>/dev/null || echo "0.0.0-0-g$(git rev-parse --short=7 HEAD)")
# Strip v prefix and -libretro suffix if present
RAW="${{RAW#v}}"
RAW="${{RAW%-libretro}}"
if echo "$RAW" | grep -qE '^[0-9]+\\.[0-9]+-[0-9]+-g'; then
    # Tag without patch: 1.0-15-gabcdef → 1.0.0+git15.gabcdef
    BASE=$(echo "$RAW" | cut -d- -f1).0
    COMMITS=$(echo "$RAW" | cut -d- -f2)
    HASH=$(echo "$RAW" | cut -d- -f3)
    VERSION="${{BASE}}+git${{COMMITS}}.${{HASH}}"
elif echo "$RAW" | grep -qE '^[0-9]+\\.[0-9]+\\.[0-9]+-[0-9]+-g'; then
    # Normal: 1.0.2-15-gabcdef → 1.0.2+git15.gabcdef
    BASE=$(echo "$RAW" | cut -d- -f1)
    COMMITS=$(echo "$RAW" | cut -d- -f2)
    HASH=$(echo "$RAW" | cut -d- -f3)
    VERSION="${{BASE}}+git${{COMMITS}}.${{HASH}}"
else
    VERSION="$RAW"
fi
cd "$BUILD_DIR"
ok "Version: $VERSION"

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
Conflicts: sameboy
Replaces: sameboy
Provides: sameboy
Homepage: {self.homepage}
Description: {self.description}
 Development build from master. Includes SDL2 frontend, boot ROMs, shaders,
 palettes, and desktop integration.
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
