"""
Base class for all package definitions.

Each package in the packages/ directory subclasses PackageBase and defines:
  - metadata (name, version, source URL, etc.)
  - apt_build_deps: system packages needed to compile
  - write_build_script(): generates the bash script that builds the .deb
"""

from __future__ import annotations

import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Literal


VersionType = Literal["git_latest", "git_tag", "url"]


class PackageBase(ABC):
    # --- Metadata (set as class attributes in subclasses) ---

    # Package name as it will appear in dpkg (e.g. "libdvdcss")
    name: str

    # Human-readable name shown in the UI (e.g. "libdvdcss")
    display_name: str

    # "latest" to always build HEAD/latest tag, or a specific version string
    # e.g. "1.4.3", "R73"
    version: str

    # How to interpret the version:
    #   git_latest  - clone repo and use the latest git tag
    #   git_tag     - clone repo and checkout this specific tag
    #   url         - download a tarball from source_url directly
    version_type: VersionType

    # Git repo URL or direct tarball URL depending on version_type
    source_url: str

    # apt packages that must be installed before building
    # dep_checker will warn if any of these have no candidate
    apt_build_deps: list[str] = []

    # Optional: homepage shown in checkinstall metadata
    homepage: str = ""

    # Optional: short description for checkinstall metadata
    description: str = ""

    # ------------------------------------------------------------------ #
    #  Abstract interface — subclasses must implement these               #
    # ------------------------------------------------------------------ #

    @abstractmethod
    def write_build_script(self, build_dir: Path, output_dir: Path) -> Path:
        """
        Write a bash build script to build_dir and return its path.

        The script must:
          - Clone/download source into build_dir
          - Compile the package
          - Run checkinstall --install=no to produce a .deb
          - Move the .deb to output_dir
          - End with the standard footer (use self._script_footer())

        Args:
            build_dir:  Temporary directory to build in (~/builds/apb/<name>)
            output_dir: Where to put the finished .deb (repo/output/)

        Returns:
            Path to the written .sh script file
        """
        ...

    # ------------------------------------------------------------------ #
    #  Helpers available to subclasses                                    #
    # ------------------------------------------------------------------ #

    def get_effective_version(self) -> str:
        """
        Return the version string to display in the UI.
        For git_latest this queries the remote for the latest tag.

        Uses normalised version sorting so mixed naming conventions
        (e.g. v1_2_8 vs 1.5.0 in the same repo) resolve correctly.
        """
        if self.version != "latest":
            return self.version

        if self.version_type in ("git_latest", "git_tag"):
            try:
                result = subprocess.run(
                    ["git", "ls-remote", "--tags", self.source_url],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                # Collect all tags, skip dereference lines (^{})
                tags = []
                for line in result.stdout.splitlines():
                    if "refs/tags/" in line and "^{}" not in line:
                        tag = line.split("refs/tags/")[-1].strip()
                        tags.append(tag)

                if not tags:
                    return "latest"

                # Normalise each tag to a dotted version for sorting,
                # keeping the original tag alongside so we can return it.
                def normalise(tag: str) -> str:
                    t = tag.lstrip("v")
                    t = t.replace("_", ".")
                    return t

                def version_key(tag: str) -> tuple:
                    """Convert a tag to a sortable int tuple, e.g. '1.5.0' → (1, 5, 0)."""
                    try:
                        return tuple(int(x) for x in normalise(tag).split("."))
                    except ValueError:
                        return (0,)

                versioned = [t for t in tags if version_key(t) != (0,)]
                if versioned:
                    versioned.sort(key=version_key)
                    latest_tag = versioned[-1]
                    return normalise(latest_tag)

            except Exception:
                pass
        return "latest"

    def get_cached_source(self, cache_dir: Path) -> Path | None:
        """
        Return path to cached source archive if present, else None.
        Looks for any file in cache_dir whose name contains the package
        name and version.
        """
        if not cache_dir.exists():
            return None
        version = self.version if self.version != "latest" else ""
        for f in cache_dir.iterdir():
            if self.name in f.name and (not version or version in f.name):
                return f
        return None

    def get_built_deb(self, output_dir: Path) -> Path | None:
        """Return path to the most recently built .deb in output_dir, or None."""
        if not output_dir.exists():
            return None
        debs = sorted(
            [f for f in output_dir.iterdir() if f.name.startswith(self.name) and f.suffix == ".deb"],
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        return debs[0] if debs else None

    def _script_header(self) -> str:
        """Standard bash script header."""
        return """\
#!/bin/bash
set -e

# Colours
GREEN='\\033[0;32m'
RED='\\033[0;31m'
YELLOW='\\033[1;33m'
CYAN='\\033[0;36m'
NC='\\033[0m'

step() { echo -e "\\n${CYAN}==>${NC} $1"; }
ok()   { echo -e "${GREEN}✓${NC} $1"; }
die()  { echo -e "${RED}✗ $1${NC}" >&2; exit 1; }

# Always keep the window open — show success or failure message on exit
_APB_STATUS=failed
_apb_finish() {
    echo ""
    echo "========================================="
    if [ "$_APB_STATUS" = "ok" ]; then
        echo -e "${GREEN}All done!${NC} Press Enter to close..."
    else
        echo -e "${RED}Build FAILED${NC} — see error above. Press Enter to close..."
    fi
    echo "========================================="
    read
}
trap _apb_finish EXIT
"""

    def _script_footer(self) -> str:
        """Mark build as successful — the EXIT trap shows the final message."""
        return """
_APB_STATUS=ok
"""
