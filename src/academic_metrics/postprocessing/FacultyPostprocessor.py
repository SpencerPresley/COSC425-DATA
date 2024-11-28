from __future__ import annotations

from typing import Dict, TYPE_CHECKING

from .BasePostprocessor import BasePostprocessor
from academic_metrics.configs import configure_logging, DEBUG
from academic_metrics.dataclass_models import CategoryInfo

if TYPE_CHECKING:
    from academic_metrics.utils import MinHashUtility


class FacultyPostprocessor(BasePostprocessor):
    def __init__(self, minhash_util: MinHashUtility, threshold: float = 0.5):
        """
        Initialize the FacultyPostprocessor with a MinHashUtility instance.

        Args:
            minhash_util (MinHashUtility): A MinHashUtility instance for minhash operations.
        """
        self.logger = configure_logging(
            module_name=__name__,
            log_file_name="faculty_postprocessor",
            log_level=DEBUG,
        )

        self.logger.info("Initializing FacultyPostprocessor...")
        super().__init__(
            attribute_name="faculty", minhash_util=minhash_util, threshold=threshold
        )

    def remove_near_duplicates(
        self,
        *,
        category_dict: Dict[str, CategoryInfo],
    ) -> Dict[str, CategoryInfo]:
        """
        Remove near-duplicate faculty names from the category dictionary.

        Args:
            category_dict (Dict[str, CategoryInfo]): A dictionary mapping category names
                                                    to CategoryInfo objects.

        Returns:
            Dict[str, CategoryInfo]: A dictionary mapping category names to CategoryInfo
                                    objects with near-duplicate faculty names removed.
        """
        self.logger.info("Processing faculty names across categories...")
        processed_dict = super().remove_near_duplicates(category_dict=category_dict)
        self.logger.info("Faculty names processed.")
        return processed_dict
