"""
vapoursynth-znedi3 — Neural Network Edge Directed Interpolation 3 for VapourSynth.

High-quality edge-directed field interpolation for deinterlacing and upscaling.
Provides core.znedi3.znedi3(). Includes bundled nnedi3_weights.bin.

Uses git submodules (graphengine + vsxx). SIMD via C++ intrinsics (no nasm).

Requires VapourSynth to be installed first.

Source: https://github.com/sekrit-twc/znedi3
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from core.package_base import PackageBase


class VapourSynthZnedi3(PackageBase):
    name = "vapoursynth-znedi3"
    display_name = "vapoursynth-znedi3"
    version = "latest"
    version_type = "git_latest"
    source_url = "https://github.com/sekrit-twc/znedi3.git"
    homepage = "https://github.com/sekrit-twc/znedi3"
    description = "Neural Network Edge Directed Interpolation 3 (nnedi3) VapourSynth plugin"

    apt_build_deps = [
        "git",
        "g++",
        "make",
        "pkg-config",
    ]

    def get_effective_version(self) -> str:
        """Tags use lowercase r-prefix: r1, r2, r2.1, etc."""
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
                    if len(tag) > 1 and tag[0].lower() == "r" and tag[1].isdigit():
                        r_tags.append(tag)
            if r_tags:
                def _key(t: str) -> tuple:
                    return tuple(int(n) for n in re.findall(r"\d+", t))
                r_tags.sort(key=_key)
                return r_tags[-1].lstrip("rR")  # e.g. "r2.1" → "2.1"
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

# ── Find latest r-series tag ────────────────────────────────────────────
# Tags use lowercase r-prefix with dotted versions: r1, r2, r2.1 ...
step "Finding latest znedi3 release tag..."

LATEST_TAG=$(git ls-remote --tags "$REPO_URL" \\
    | grep -v '\\^' \\
    | sed 's|.*refs/tags/||' \\
    | grep -iE '^r[0-9]' \\
    | sort -V \\
    | tail -1)

if [ -z "$LATEST_TAG" ]; then
    die "Could not determine latest znedi3 release tag"
fi

VERSION=$(echo "$LATEST_TAG" | sed 's/^[rR]//')
ok "Latest tag: $LATEST_TAG  →  version: $VERSION"

# ── Clone with submodules ──────────────────────────────────────────────
# znedi3 requires two git submodules: graphengine and vsxx (VS C++ wrapper).
# Without them the build fails immediately.
step "Cloning znedi3 $LATEST_TAG (with submodules)..."
rm -rf znedi3
git clone --depth 1 --branch "$LATEST_TAG" "$REPO_URL" znedi3
cd znedi3
git submodule update --init --recursive

# ── Build ──────────────────────────────────────────────────────────────
# No install target — produces vsznedi3.so in the repo root.
# X86=1 enables SSE/AVX/AVX2 SIMD paths via C++ intrinsics (no nasm needed).
step "Building znedi3..."
make -j$(nproc) X86=1

# ── Stage manually ─────────────────────────────────────────────────────
# Both vsznedi3.so and nnedi3_weights.bin must be in the same VS plugin dir.
step "Staging install..."
STAGING=$(mktemp -d)
VSDIR="$STAGING/usr/lib/x86_64-linux-gnu/vapoursynth"
mkdir -p "$VSDIR"
cp vsznedi3.so "$VSDIR/"
cp nnedi3_weights.bin "$VSDIR/"
ok "Staged: vsznedi3.so + nnedi3_weights.bin → $VSDIR/"

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
dpkg-deb --root-owner-group --build "$STAGING" "$DEB_FILE"
rm -rf "$STAGING"
ok "Built: $DEB_FILE"
""" + self._script_footer()

        script_path.write_text(script)
        return script_path
