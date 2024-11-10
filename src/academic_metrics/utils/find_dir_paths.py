from pathlib import Path
from typing import cast, Optional


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
