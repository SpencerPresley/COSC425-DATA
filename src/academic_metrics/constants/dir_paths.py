from pathlib import Path
from typing import Optional, cast


def find_project_root(marker: str = "COSC425-DATA") -> Path:
    """Find the repository root directory."""
    current = Path(__file__).resolve()
    while current.parent != current:
        if current.name == marker:
            return current
        current = current.parent
    raise FileNotFoundError(
        f"Could not find repository root '{marker}'. "
        "Are you running from the correct directory?"
    )


def find_src_root(repo_root: Path = None) -> Path:
    """Find the source code root directory (PythonCode)."""
    if cast(Optional[Path], repo_root) is None:
        repo_root = find_project_root()
    src_dir = repo_root / "src"
    if not src_dir.exists():
        raise FileNotFoundError(
            "Could not find source directory 'PythonCode'. "
            "Has the project structure changed?"
        )
    return src_dir


_PROJECT_ROOT = find_project_root()
_SRC_ROOT = find_src_root()
_ACADEMIC_METRICS_ROOT = _PROJECT_ROOT / "academic_metrics"
_DATA_ROOT = _SRC_ROOT / "data"
_DATA_CORE_ROOT = _DATA_ROOT / "core"
_DATA_OTHER_ROOT = _DATA_ROOT / "other"
SPLIT_FILES_DIR_PATH = _DATA_CORE_ROOT / "crossref_split_files"
INPUT_FILES_DIR_PATH = _DATA_CORE_ROOT / "input_files"
OUTPUT_FILES_DIR_PATH = _DATA_CORE_ROOT / "output_files"

_ACADEMIC_METRICS_PACKAGE_ROOT = _SRC_ROOT / "academic_metrics"
LOG_DIR_PATH = _ACADEMIC_METRICS_PACKAGE_ROOT / "logs"
