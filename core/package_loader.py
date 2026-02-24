"""
Auto-discovers all PackageBase subclasses from the packages/ directory.
Just drop a new .py file in packages/ and it shows up in the UI.
"""

from __future__ import annotations

import importlib
import inspect
from pathlib import Path

from core.package_base import PackageBase

PACKAGES_DIR = Path(__file__).parent.parent / "packages"


def load_all_packages() -> list[PackageBase]:
    """Import every .py in packages/ and return instances of all PackageBase subclasses."""
    instances: list[PackageBase] = []

    for path in sorted(PACKAGES_DIR.glob("*.py")):
        if path.name.startswith("_"):
            continue
        module_name = f"packages.{path.stem}"
        try:
            module = importlib.import_module(module_name)
        except Exception as e:
            print(f"Warning: failed to load {path.name}: {e}")
            continue

        for _name, obj in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(obj, PackageBase)
                and obj is not PackageBase
                and obj.__module__ == module_name
            ):
                instances.append(obj())

    return instances
