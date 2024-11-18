import json
import logging
import os
from typing import Dict, List

from academic_metrics.constants import LOG_DIR_PATH
from academic_metrics.other.in_memory_taxonomy import TAXONOMY_AS_STRING

# Alias for the taxonomy dictionary structure to be used for type hinting the taxonomy dictionary
TaxonomyDict = Dict[str, Dict[str, List[str]]]


class Taxonomy:
    def __init__(self) -> None:
        self.log_file_path: str = os.path.join(LOG_DIR_PATH, "taxonomy_util.log")
        # Set up logger
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        self.logger.handlers = []

        # Add handler if none exists
        if not self.logger.handlers:
            handler: logging.FileHandler = logging.FileHandler(self.log_file_path)
            handler.setLevel(logging.DEBUG)
            formatter: logging.Formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        self.logger.info("Initializing Taxonomy")
        self.taxonomy: TaxonomyDict = self._load_taxonomy_from_string(
            TAXONOMY_AS_STRING
        )
        self.logger.info("Taxonomy initialized successfully")

    def __str__(self) -> str:
        return json.dumps(self.taxonomy, indent=4)

    @staticmethod
    def _load_taxonomy_from_string(taxonomy_str: str) -> TaxonomyDict:
        return json.loads(taxonomy_str)

    def get_top_categories(self) -> List[str]:
        return list(self.taxonomy.keys())

    def get_mid_categories(self, top_category: str) -> List[str]:
        return list(self.taxonomy[top_category].keys())

    def get_low_categories(self, top_category: str, mid_category: str) -> List[str]:
        return self.taxonomy[top_category][mid_category]

    def get_top_cat_for_mid_cat(self, mid_cat: str) -> str:
        top_cat: str = ""
        found: bool = False
        while not found:
            for top_cat, mid_cats in self.taxonomy.items():
                if mid_cat in mid_cats:
                    found: bool = True
                    break
            if found:
                break
        return top_cat

    def get_mid_cat_for_low_cat(self, low_cat: str) -> str:
        mid_cat: str = ""
        found: bool = False
        while not found:
            for top_cat, mid_cats in self.taxonomy.items():
                for mid_cat, low_cats in mid_cats.items():
                    if low_cat in low_cats:
                        found: bool = True
                        break
            if found:
                break
        return mid_cat

    def get_taxonomy(self) -> TaxonomyDict:
        return self.taxonomy


if __name__ == "__main__":
    taxonomy: Taxonomy = Taxonomy()
    top_categories: List[str] = taxonomy.get_top_categories()
    print(top_categories)
    for top_category in top_categories:
        mid_categories: List[str] = taxonomy.get_mid_categories(top_category)
        print(f"top category: \n{top_category}, \nmid categories: \n{mid_categories}\n")
        for mid_category in mid_categories:
            low_categories: List[str] = taxonomy.get_low_categories(
                top_category, mid_category
            )
            print(
                f"mid category: \n{mid_category}, \nlow categories: \n{low_categories}\n"
            )
        print("\n\n")
