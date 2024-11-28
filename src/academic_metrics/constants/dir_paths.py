from pathlib import Path
import os
from typing import Optional, cast


def locate_academic_metrics_root(marker: str | None = "COSC425-DATA") -> Path:
    """Find the repository root directory.

    Args:
        marker (str | None): Marker string to search for in the directory hierarchy.
            Defaults to "COSC425-DATA".
    """
    current = Path(__file__).resolve()
    while current.parent != current:
        if current.name == marker:
            return current
        current = current.parent
    raise FileNotFoundError(
        f"Could not find repository root '{marker}'. "
        "Are you running from the correct directory?"
    )


def locate_src_root(repo_root: Path | None = None) -> Path:
    """Find the source code root directory (PythonCode).

    Args:
        repo_root (Path | None): Repository root directory.
            Defaults to None.
    """
    if cast(Optional[Path], repo_root) is None:
        repo_root = locate_academic_metrics_root()
    src_dir = repo_root / "src"
    if not src_dir.exists():
        raise FileNotFoundError(
            "Could not find source directory 'PythonCode'. "
            "Has the project structure changed?"
        )
    return src_dir


if os.environ.get("READTHEDOCS") == "True":
    # Dummy paths for documentation/import
    # Without this, the `locate_academic_metrics_root` will throw the FileNotFoundError
    # everywhere this file is imported.
    _PROJECT_ROOT = Path("/dummy/project")
    _SRC_ROOT = Path("/dummy/src")
    _ACADEMIC_METRICS_ROOT = Path("/dummy/academic_metrics")
    _DATA_ROOT = Path("/dummy/data")
    _DATA_CORE_ROOT = Path("/dummy/data/core")
    _DATA_OTHER_ROOT = Path("/dummy/data/other")
    SPLIT_FILES_DIR_PATH = Path("/dummy/data/core/crossref_split_files")
    INPUT_FILES_DIR_PATH = Path("/dummy/data/core/input_files")
    OUTPUT_FILES_DIR_PATH = Path("/dummy/data/core/output_files")
    _ACADEMIC_METRICS_PACKAGE_ROOT = Path("/dummy/academic_metrics")
    LOG_DIR_PATH = Path("/dummy/academic_metrics/logs")
else:
    # System executing, set paths to actual locations
    _PROJECT_ROOT = locate_academic_metrics_root()
    _SRC_ROOT = locate_src_root()
    _ACADEMIC_METRICS_ROOT = _PROJECT_ROOT / "academic_metrics"
    _DATA_ROOT = _SRC_ROOT / "data"
    _DATA_CORE_ROOT = _DATA_ROOT / "core"
    _DATA_OTHER_ROOT = _DATA_ROOT / "other"
    SPLIT_FILES_DIR_PATH = _DATA_CORE_ROOT / "crossref_split_files"
    INPUT_FILES_DIR_PATH = _DATA_CORE_ROOT / "input_files"
    OUTPUT_FILES_DIR_PATH = _DATA_CORE_ROOT / "output_files"
    _ACADEMIC_METRICS_PACKAGE_ROOT = _SRC_ROOT / "academic_metrics"
    LOG_DIR_PATH = _ACADEMIC_METRICS_PACKAGE_ROOT / "logs"
