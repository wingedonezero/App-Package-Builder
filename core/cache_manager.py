"""
Manages the cached_downloads/ directory.

When a package specifies a direct tarball URL, the downloaded archive is
saved here so subsequent builds don't need to re-download it.
Git-based packages don't use this — they clone fresh each time (shallow).
"""

from __future__ import annotations

import hashlib
import urllib.request
from pathlib import Path


CACHE_DIR = Path(__file__).parent.parent / "cached_downloads"


def get_cache_dir() -> Path:
    CACHE_DIR.mkdir(exist_ok=True)
    return CACHE_DIR


def cached_path(filename: str) -> Path | None:
    """Return path if filename exists in cache, else None."""
    p = CACHE_DIR / filename
    return p if p.exists() else None


def list_cached() -> list[Path]:
    """Return all files currently in the cache directory."""
    if not CACHE_DIR.exists():
        return []
    return sorted(CACHE_DIR.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)


def filename_for_url(url: str, version: str, package_name: str) -> str:
    """Derive a cache filename from a URL."""
    url_filename = url.rstrip("/").split("/")[-1]
    # If the URL already has a sensible filename, use it
    if "." in url_filename and len(url_filename) > 4:
        return url_filename
    # Otherwise synthesise one
    ext = ".tar.gz"
    return f"{package_name}-{version}{ext}"


def download_to_cache(url: str, filename: str) -> Path:
    """
    Download a URL to cached_downloads/<filename>.
    Returns the path to the cached file.
    Skips download if file already exists.
    """
    dest = get_cache_dir() / filename
    if dest.exists():
        return dest

    print(f"Downloading {url} → {dest.name} ...")
    urllib.request.urlretrieve(url, dest)
    print(f"Cached: {dest}")
    return dest


def remove_cached(filename: str) -> bool:
    """Remove a file from the cache. Returns True if removed, False if not found."""
    p = CACHE_DIR / filename
    if p.exists():
        p.unlink()
        return True
    return False
