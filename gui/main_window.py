"""
Main application window.

Layout:
  ┌─────────────────────────────────────────────────────┐
  │  Package          Version   Cached   Built   Actions │
  │  ─────────────────────────────────────────────────  │
  │  libdvdcss        1.4.3     -        -       [deps] [build] │
  ├─────────────────────────────────────────────────────┤
  │ Dep warnings (shown only when problems exist)        │
  └─────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core import builder, dep_checker
from core.cache_manager import CACHE_DIR
from core.builder import OUTPUT_DIR
from core.dep_checker import DepStatus
from core.package_base import PackageBase
from core.package_loader import load_all_packages


# Column indices
COL_NAME = 0
COL_VERSION = 1
COL_CACHED = 2
COL_BUILT = 3
COL_DEPS = 4
COL_BUILD = 5

COLUMNS = ["Package", "Version", "Cached", "Built", "Deps", "Build"]


class VersionFetchThread(QThread):
    """Fetches live version strings from git remotes without blocking the UI."""
    result = Signal(int, str)  # (row, version_string)

    def __init__(self, row: int, package: PackageBase):
        super().__init__()
        self.row = row
        self.package = package

    def run(self):
        version = self.package.get_effective_version()
        self.result.emit(self.row, version)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("App Package Builder")
        self.setMinimumSize(820, 480)

        self._packages = load_all_packages()
        self._build_procs: dict[str, subprocess.Popen] = {}
        self._version_threads: list[VersionFetchThread] = []

        self._setup_ui()
        self._populate_table()

    # ------------------------------------------------------------------ #
    #  UI setup                                                            #
    # ------------------------------------------------------------------ #

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Title
        title = QLabel("App Package Builder")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        subtitle = QLabel(
            "Build .deb packages from source for software not available in Debian repos."
        )
        subtitle.setStyleSheet("color: #888;")
        layout.addWidget(subtitle)

        # Warning panel (hidden by default)
        self._warning_box = QTextEdit()
        self._warning_box.setReadOnly(True)
        self._warning_box.setMaximumHeight(100)
        self._warning_box.setStyleSheet(
            "background: #3b1f00; color: #ffb347; border: 1px solid #ff8c00;"
            "font-family: monospace; font-size: 12px;"
        )
        self._warning_box.hide()
        layout.addWidget(self._warning_box)

        # Package table
        self._table = QTableWidget(0, len(COLUMNS))
        self._table.setHorizontalHeaderLabels(COLUMNS)
        self._table.horizontalHeader().setSectionResizeMode(COL_NAME, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(COL_VERSION, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(COL_CACHED, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(COL_BUILT, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(COL_DEPS, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(COL_BUILD, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().hide()
        layout.addWidget(self._table)

        # Bottom bar
        bottom = QHBoxLayout()
        refresh_btn = QPushButton("↻  Refresh Status")
        refresh_btn.clicked.connect(self._refresh_all)
        bottom.addWidget(refresh_btn)
        bottom.addStretch()

        output_label = QLabel(f"Output: {OUTPUT_DIR}")
        output_label.setStyleSheet("color: #888; font-size: 11px;")
        bottom.addWidget(output_label)
        layout.addLayout(bottom)

    # ------------------------------------------------------------------ #
    #  Table population                                                    #
    # ------------------------------------------------------------------ #

    def _populate_table(self):
        self._table.setRowCount(len(self._packages))

        for row, pkg in enumerate(self._packages):
            self._set_name_cell(row, pkg)
            self._set_version_cell(row, pkg)
            self._set_cached_cell(row, pkg)
            self._set_built_cell(row, pkg)
            self._set_deps_button(row, pkg)
            self._set_build_button(row, pkg)

    def _set_name_cell(self, row: int, pkg: PackageBase):
        item = QTableWidgetItem(pkg.display_name)
        item.setToolTip(pkg.description)
        self._table.setItem(row, COL_NAME, item)

    def _set_version_cell(self, row: int, pkg: PackageBase):
        item = QTableWidgetItem("fetching..." if pkg.version == "latest" else pkg.version)
        item.setForeground(QColor("#aaaaaa"))
        self._table.setItem(row, COL_VERSION, item)

        if pkg.version == "latest":
            thread = VersionFetchThread(row, pkg)
            thread.result.connect(self._on_version_fetched)
            self._version_threads.append(thread)
            thread.start()

    def _set_cached_cell(self, row: int, pkg: PackageBase):
        cached = pkg.get_cached_source(CACHE_DIR)
        if cached:
            item = QTableWidgetItem("✓")
            item.setForeground(QColor("#44cc44"))
            item.setToolTip(str(cached))
        else:
            item = QTableWidgetItem("—")
            item.setForeground(QColor("#666666"))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table.setItem(row, COL_CACHED, item)

    def _set_built_cell(self, row: int, pkg: PackageBase):
        deb = pkg.get_built_deb(OUTPUT_DIR)
        if deb:
            item = QTableWidgetItem("✓")
            item.setForeground(QColor("#44cc44"))
            item.setToolTip(str(deb))
        else:
            item = QTableWidgetItem("—")
            item.setForeground(QColor("#666666"))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table.setItem(row, COL_BUILT, item)

    def _set_deps_button(self, row: int, pkg: PackageBase):
        btn = QPushButton("Check & Install Deps")
        btn.setFixedHeight(28)
        btn.clicked.connect(lambda _checked, p=pkg: self._on_deps_clicked(p))
        self._table.setCellWidget(row, COL_DEPS, btn)

    def _set_build_button(self, row: int, pkg: PackageBase):
        btn = QPushButton("Build .deb")
        btn.setFixedHeight(28)
        btn.setStyleSheet("QPushButton { background: #1d6fa4; color: white; }"
                          "QPushButton:hover { background: #2588c2; }")
        btn.clicked.connect(lambda _checked, p=pkg, r=row: self._on_build_clicked(p, r))
        self._table.setCellWidget(row, COL_BUILD, btn)

    # ------------------------------------------------------------------ #
    #  Button handlers                                                     #
    # ------------------------------------------------------------------ #

    def _on_deps_clicked(self, pkg: PackageBase):
        """Check deps, show warnings for any problems, then offer to install good ones."""
        if not pkg.apt_build_deps:
            QMessageBox.information(self, "No Dependencies", f"{pkg.display_name} has no apt build dependencies defined.")
            return

        results = dep_checker.check_deps(pkg.apt_build_deps)
        ok_pkgs = [r.package for r in results if r.status == DepStatus.OK]
        problem_pkgs = [r for r in results if r.status != DepStatus.OK]

        # Show warnings
        if problem_pkgs:
            lines = [f"⚠ Dependency problems for {pkg.display_name}:\n"]
            for r in problem_pkgs:
                status_str = "no candidate" if r.status == DepStatus.MISSING_CANDIDATE else "not found"
                lines.append(f"  • {r.package} — {status_str}")
                if r.warning:
                    lines.append(f"    {r.warning}")
            self._show_warnings("\n".join(lines))

        if not ok_pkgs:
            QMessageBox.warning(
                self, "Cannot Install Dependencies",
                "All dependencies have problems — nothing to install.\n"
                "See the warning panel for details."
            )
            return

        # Confirm install of the good ones
        pkg_list = "\n  • ".join(ok_pkgs)
        reply = QMessageBox.question(
            self,
            "Install Build Dependencies",
            f"Install the following packages via apt?\n\n  • {pkg_list}"
            + (f"\n\n⚠ {len(problem_pkgs)} dep(s) have issues and will be skipped." if problem_pkgs else ""),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            builder.launch_dep_install(ok_pkgs)

    def _on_build_clicked(self, pkg: PackageBase, row: int):
        """Launch the build in a new Konsole window."""
        # Check if a build for this package is already running
        existing = self._build_procs.get(pkg.name)
        if existing and existing.poll() is None:
            QMessageBox.information(
                self, "Already Building",
                f"{pkg.display_name} is already building in another window."
            )
            return

        proc = builder.launch_build(pkg)
        self._build_procs[pkg.name] = proc

        # Update the build button to show "Building..."
        btn = self._table.cellWidget(row, COL_BUILD)
        if btn:
            btn.setText("Building...")
            btn.setEnabled(False)
            btn.setStyleSheet("QPushButton { background: #555; color: #aaa; }")

    # ------------------------------------------------------------------ #
    #  Slots                                                               #
    # ------------------------------------------------------------------ #

    def _on_version_fetched(self, row: int, version: str):
        item = self._table.item(row, COL_VERSION)
        if item:
            item.setText(version)
            item.setForeground(QColor("#dddddd"))

    def _show_warnings(self, text: str):
        self._warning_box.setPlainText(text)
        self._warning_box.show()

    def _refresh_all(self):
        """Refresh cached/built status columns and re-enable finished build buttons."""
        self._warning_box.hide()

        for row, pkg in enumerate(self._packages):
            self._set_cached_cell(row, pkg)
            self._set_built_cell(row, pkg)

            # Re-enable build button if the konsole window has closed
            proc = self._build_procs.get(pkg.name)
            if proc and proc.poll() is not None:
                btn = self._table.cellWidget(row, COL_BUILD)
                if btn:
                    btn.setText("Build .deb")
                    btn.setEnabled(True)
                    btn.setStyleSheet(
                        "QPushButton { background: #1d6fa4; color: white; }"
                        "QPushButton:hover { background: #2588c2; }"
                    )
