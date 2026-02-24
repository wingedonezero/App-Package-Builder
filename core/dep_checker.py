"""
Dependency checker — inspects apt-cache policy for each build dep
and classifies them as: ok, missing_candidate, or not_found.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from enum import Enum, auto


class DepStatus(Enum):
    OK = auto()               # Candidate version exists, safe to install
    MISSING_CANDIDATE = auto()  # In dpkg database but no installable candidate
                                # (e.g. dmo package after removing that repo)
    NOT_FOUND = auto()        # Not known to apt at all


@dataclass
class DepResult:
    package: str
    status: DepStatus
    candidate: str | None   # Version string if available, else None
    warning: str | None     # Human-readable warning message, else None


def check_dep(package: str) -> DepResult:
    """Run apt-cache policy on a single package and return its status."""
    try:
        result = subprocess.run(
            ["apt-cache", "policy", package],
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = result.stdout
    except Exception as e:
        return DepResult(
            package=package,
            status=DepStatus.NOT_FOUND,
            candidate=None,
            warning=f"apt-cache failed: {e}",
        )

    if not output.strip():
        return DepResult(
            package=package,
            status=DepStatus.NOT_FOUND,
            candidate=None,
            warning=f"'{package}' is not known to apt.",
        )

    candidate: str | None = None
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith("Candidate:"):
            value = stripped.split(":", 1)[1].strip()
            if value and value != "(none)":
                candidate = value
            break

    if candidate is None:
        # Package is in the database but has no installable candidate.
        # This typically means it came from a repo that's now removed/pinned out.
        return DepResult(
            package=package,
            status=DepStatus.MISSING_CANDIDATE,
            candidate=None,
            warning=(
                f"'{package}' has no installable candidate. "
                "It may be from a repo that's been removed or pinned out. "
                "This package will need to be built from source or sourced elsewhere."
            ),
        )

    return DepResult(
        package=package,
        status=DepStatus.OK,
        candidate=candidate,
        warning=None,
    )


def check_deps(packages: list[str]) -> list[DepResult]:
    """Check a list of apt package names and return results for all."""
    return [check_dep(pkg) for pkg in packages]


def has_warnings(results: list[DepResult]) -> bool:
    return any(r.status != DepStatus.OK for r in results)
