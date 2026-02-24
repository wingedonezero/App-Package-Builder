"""
CCExtractor — extract subtitles and closed captions from video files.

Pre-built Debian 13 (Trixie) amd64 .deb downloaded directly from GitHub
releases — no compilation required.

Also available: ccextractor-hardsubx (burned-in subtitle extraction, adds
FFmpeg + Tesseract deps). Add a second package entry if needed.

Source: https://github.com/CCExtractor/ccextractor
"""

from __future__ import annotations

from pathlib import Path

from core.package_base import PackageBase


class CcExtractor(PackageBase):
    name = "ccextractor"
    display_name = "CCExtractor"
    version = "latest"
    version_type = "git_latest"
    source_url = "https://github.com/CCExtractor/ccextractor.git"
    homepage = "https://ccextractor.org"
    description = "Tool used to extract subtitles and closed captions from video files"

    # Pre-built .deb — no compilation needed, no build deps
    apt_build_deps = []

    def write_build_script(self, build_dir: Path, output_dir: Path) -> Path:
        script_path = build_dir / "build.sh"

        script = self._script_header() + f"""
BUILD_DIR="{build_dir}"
OUTPUT_DIR="{output_dir}"

# ── Find latest release tag ────────────────────────────────────────────
step "Finding latest release tag..."

LATEST_TAG=$(git ls-remote --tags "{self.source_url}" \\
    | grep -v '\\^{{}}' \\
    | sed 's|.*refs/tags/||' \\
    | grep '^v[0-9]' \\
    | sort -V \\
    | tail -1)

if [ -z "$LATEST_TAG" ]; then
    die "Could not determine latest release tag"
fi

VERSION="${{LATEST_TAG#v}}"
ok "Latest release: $LATEST_TAG  →  version: $VERSION"

# ── Download pre-built Debian 13 .deb ─────────────────────────────────
step "Downloading ccextractor_${{VERSION}}_debian13_amd64.deb..."

DEB_NAME="ccextractor_${{VERSION}}_debian13_amd64.deb"
DEB_URL="https://github.com/CCExtractor/ccextractor/releases/download/$LATEST_TAG/$DEB_NAME"
DEST="$OUTPUT_DIR/$DEB_NAME"

python3 -c "import urllib.request; urllib.request.urlretrieve('$DEB_URL', '$DEST')"

ok "Downloaded: $DEST"
""" + self._script_footer()

        script_path.write_text(script)
        return script_path
