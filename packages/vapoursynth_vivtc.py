"""
vapoursynth-vivtc — VIVTC/VFM field matching and VDecimate decimation filters.

Used for inverse telecine (IVTC) — recovering progressive frames from
interlaced/telecined video. Provides core.vivtc.VFM() and core.vivtc.VDecimate().

Requires VapourSynth to be installed first.

Source: https://github.com/vapoursynth/vivtc
"""

from __future__ import annotations

from pathlib import Path

from core.package_base import PackageBase


class VapourSynthVivtc(PackageBase):
    name = "vapoursynth-vivtc"
    display_name = "vapoursynth-vivtc"
    version = "latest"
    version_type = "git_latest"
    source_url = "https://github.com/vapoursynth/vivtc.git"
    homepage = "https://github.com/vapoursynth/vivtc"
    description = "VFM field matcher and VDecimate decimation filter for VapourSynth (IVTC)"

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
step "Finding latest VIVTC release tag..."

LATEST_TAG=$(git ls-remote --tags "$REPO_URL" \\
    | grep -v '\\^{{}}' \\
    | sed 's|.*refs/tags/||' \\
    | awk '{{tag=$0; norm=tag; sub(/^[vRr]/,"",norm); gsub(/_/,".",norm); print norm"\\t"tag}}' \\
    | sort -V -k1,1 \\
    | tail -1 \\
    | cut -f2)

if [ -z "$LATEST_TAG" ]; then
    die "Could not determine latest VIVTC release tag"
fi

VERSION="${{LATEST_TAG#v}}"
VERSION="${{VERSION#R}}"
ok "Latest tag: $LATEST_TAG  →  version: $VERSION"

# ── Clone ──────────────────────────────────────────────────────────────
step "Cloning VIVTC $LATEST_TAG..."
rm -rf vivtc
git clone --depth 1 --branch "$LATEST_TAG" "$REPO_URL" vivtc
cd vivtc

# ── Build ──────────────────────────────────────────────────────────────
step "Configuring with meson..."
meson setup build --prefix=/usr --buildtype=release

step "Building..."
ninja -C build

# ── Stage into DESTDIR ─────────────────────────────────────────────────
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
Section: video
Priority: optional
Depends: vapoursynth
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
