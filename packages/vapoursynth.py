"""
VapourSynth — video processing framework.

Built from source because Debian doesn't package it.
Includes the core library, Python bindings, VSScript, and vspipe.

Source: https://github.com/vapoursynth/vapoursynth
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from core.package_base import PackageBase


class VapourSynth(PackageBase):
    name = "vapoursynth"
    display_name = "VapourSynth"
    version = "latest"
    version_type = "git_latest"
    source_url = "https://github.com/vapoursynth/vapoursynth.git"
    homepage = "https://www.vapoursynth.com"
    description = "A powerful video processing framework with a Python scripting API"

    apt_build_deps = [
        "git",
        "meson",
        "ninja-build",
        "g++",
        "pkg-config",
        "libzimg-dev",
        "python3-dev",
        "cython3",
        "nasm",
    ]

    def get_effective_version(self) -> str:
        """VapourSynth tags use R-prefix format: R72, R73, etc."""
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
                return r_tags[-1]  # e.g. "R73"
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
# VapourSynth uses R-prefixed tags: R72, R73, R74 ...
step "Finding latest VapourSynth release tag..."

LATEST_TAG=$(git ls-remote --tags "$REPO_URL" \\
    | grep -v '\\^{{}}' \\
    | sed 's|.*refs/tags/||' \\
    | grep '^R[0-9]\\+$' \\
    | sed 's/^R//' \\
    | sort -n \\
    | tail -1 \\
    | sed 's/^/R/')

if [ -z "$LATEST_TAG" ]; then
    die "Could not determine latest VapourSynth release tag"
fi

# Strip R prefix for the .deb version number  (R73 → 73)
VERSION="${{LATEST_TAG#R}}"
ok "Latest tag: $LATEST_TAG  →  .deb version: $VERSION"

# ── Clone at that tag ──────────────────────────────────────────────────
step "Cloning VapourSynth $LATEST_TAG..."
rm -rf vapoursynth
git clone --depth 1 --branch "$LATEST_TAG" "$REPO_URL" vapoursynth
cd vapoursynth

# ── Build ──────────────────────────────────────────────────────────────
step "Configuring with meson..."
meson setup build \\
    --prefix=/usr \\
    --buildtype=release \\
    -Denable_vspipe=true \\
    -Denable_vsscript=true \\
    -Denable_python_module=true

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
Depends: libzimg2, python3 (>= 3.8)
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
