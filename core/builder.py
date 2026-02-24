"""
Launches a Konsole window to run a package's build script.
Each build gets its own Konsole window so output is visible and
interactive (handles sudo password prompts naturally).
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from core.package_base import PackageBase

# Project root (two levels up from this file: core/ → project root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Where builds happen — git clones + build artifacts, inside the repo but gitignored
BUILDS_BASE = PROJECT_ROOT / "builds"

# Where finished .deb files land (inside the repo)
OUTPUT_DIR = PROJECT_ROOT / "output"


def launch_build(package: PackageBase) -> subprocess.Popen:
    """
    Write the package's build script and launch it in a new Konsole window.
    Returns the Popen handle for the konsole process so the UI can track it.
    """
    build_dir = BUILDS_BASE / package.name
    build_dir.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Ask the package to write its build script
    script_path = package.write_build_script(build_dir, OUTPUT_DIR)
    script_path.chmod(0o755)

    # Konsole command: run script, keep window open on finish via the
    # "Press Enter to close..." footer baked into every build script
    konsole_cmd = [
        "konsole",
        "--noclose",
        "-e",
        "bash",
        str(script_path),
    ]

    proc = subprocess.Popen(konsole_cmd)
    return proc


def launch_dep_install(packages: list[str]) -> subprocess.Popen:
    """
    Open a Konsole window that runs apt install for the given packages.
    Used by the 'Install Build Deps' button.
    """
    pkg_str = " ".join(packages)

    # Write a small inline script
    script_content = f"""\
#!/bin/bash
set -e
echo "Installing build dependencies..."
echo ""
sudo apt install -y {pkg_str}
echo ""
echo "========================================="
echo "Done! Press Enter to close..."
echo "========================================="
read
"""
    # Write to a temp file (it only lives for this session)
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        prefix="apb_deps_",
        suffix=".sh",
        delete=False,
    )
    tmp.write(script_content)
    tmp.flush()
    Path(tmp.name).chmod(0o755)

    konsole_cmd = [
        "konsole",
        "--noclose",
        "-e",
        "bash",
        tmp.name,
    ]
    return subprocess.Popen(konsole_cmd)
