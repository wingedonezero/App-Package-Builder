"""
vapoursynth-bwdif — Bob Weaver Deinterlacing Filter for VapourSynth.

Motion-adaptive deinterlacing ported from FFmpeg's libavfilter.
Provides core.bwdif.BwDif().

Requires VapourSynth to be installed first.

Source: https://github.com/HomeOfVapourSynthEvolution/VapourSynth-Bwdif
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from core.package_base import PackageBase


class VapourSynthBwdif(PackageBase):
    name = "vapoursynth-bwdif"
    display_name = "vapoursynth-bwdif"
    version = "latest"
    version_type = "git_latest"
    source_url = "https://github.com/HomeOfVapourSynthEvolution/VapourSynth-Bwdif.git"
    homepage = "https://github.com/HomeOfVapourSynthEvolution/VapourSynth-Bwdif"
    description = "Bob Weaver Deinterlacing Filter for VapourSynth, ported from FFmpeg"

    apt_build_deps = [
        "git",
        "meson",
        "ninja-build",
        "gcc",
        "nasm",
        "pkg-config",
    ]

    def get_effective_version(self) -> str:
        """HomeOfVapourSynthEvolution repos use R-prefix tags: R6, R7, etc."""
        try:
            result = subprocess.run(
                ["git", "ls-remote", "--tags", self.source_url],
                capture_output=True,
                text=True,
                timeout=10,
            )
            r_tags = []
            for line in result.stdout.splitlines():
                if "refs/tags/" in line and "^{}" not in line:
                    tag = line.split("refs/tags/")[-1].strip()
                    if tag.startswith("R") and tag[1:].isdigit():
                        r_tags.append(tag)
            if r_tags:
                r_tags.sort(key=lambda t: int(t[1:]))
                return r_tags[-1]
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

# ── Find latest R-series tag ────────────────────────────────────────────
# HomeOfVapourSynthEvolution repos use R-prefixed tags: R6, R7, R8 ...
step "Finding latest bwdif release tag..."

LATEST_TAG=$(git ls-remote --tags "$REPO_URL" \\
    | grep -v '\\^{{}}' \\
    | sed 's|.*refs/tags/||' \\
    | grep '^R[0-9]\\+$' \\
    | sed 's/^R//' \\
    | sort -n \\
    | tail -1 \\
    | sed 's/^/R/')

if [ -z "$LATEST_TAG" ]; then
    die "Could not determine latest bwdif release tag"
fi

VERSION="${{LATEST_TAG#R}}"
ok "Latest tag: $LATEST_TAG  →  version: $VERSION"

# ── Clone ──────────────────────────────────────────────────────────────
step "Cloning VapourSynth-Bwdif $LATEST_TAG..."
rm -rf VapourSynth-Bwdif
git clone --depth 1 --branch "$LATEST_TAG" "$REPO_URL" VapourSynth-Bwdif
cd VapourSynth-Bwdif

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
