from academic_metrics.utils import find_project_root, find_src_root

_PROJECT_ROOT = find_project_root()
_SRC_ROOT = find_src_root()
_ACADEMIC_METRICS_ROOT = _PROJECT_ROOT / "academic_metrics"
_DATA_ROOT = _SRC_ROOT / "data"
_DATA_CORE_ROOT = _DATA_ROOT / "core"
_DATA_OTHER_ROOT = _DATA_ROOT / "other"
SPLIT_FILES_DIR_PATH = _DATA_CORE_ROOT / "crossref_split_files"
INPUT_FILES_DIR_PATH = _DATA_CORE_ROOT / "input_files"
OUTPUT_FILES_DIR_PATH = _DATA_CORE_ROOT / "output_files"
