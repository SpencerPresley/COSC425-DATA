import json
import logging
import os
from typing import Dict, List, Literal

from academic_metrics.configs import configure_logging, DEBUG
from academic_metrics.other.in_memory_taxonomy import TAXONOMY_AS_STRING

# Alias for the taxonomy dictionary structure to be used for type hinting the taxonomy dictionary
TaxonomyDict = Dict[str, Dict[str, List[str]]]


class Taxonomy:
    def __init__(self) -> None:
        self.logger = configure_logging(
            module_name=__name__,
            log_file_name="taxonomy_util",
            log_level=DEBUG,
        )

        self.logger.info("Initializing Taxonomy")
        self.taxonomy: TaxonomyDict = self._load_taxonomy_from_string(
            TAXONOMY_AS_STRING, self.logger
        )
        self.logger.info("Taxonomy initialized successfully")

        self.all_top_categories: List[str] = self._set_all_top_categories()
        self.all_mid_categories: List[str] = self._set_all_mid_categories()
        self.all_low_categories: List[str] = self._set_all_low_categories()

    def __str__(self) -> str:
        self.logger.info("Converting taxonomy to string")
        taxonomy_str: str = json.dumps(self.taxonomy, indent=4)
        self.logger.info("Taxonomy string converted successfully")
        return taxonomy_str

    def _set_all_top_categories(self) -> List[str]:
        """Sets all top categories from the taxonomy.

        Returns:
            List[str]: A list of all top categories in the taxonomy
        """
        return self.get_top_categories()

    def _set_all_mid_categories(self) -> List[str]:
        """Sets all mid categories from the taxonomy.

        Returns:
            List[str]: A list of all mid categories in the taxonomy
        """
        top_cats: List[str] = self.get_top_categories()
        mid_cats: List[str] = []
        for top_cat in top_cats:
            mid_cats.extend(self.get_mid_categories(top_cat))
        return mid_cats

    def _set_all_low_categories(self) -> List[str]:
        """Sets all low categories from the taxonomy.

        Returns:
            List[str]: A list of all low categories in the taxonomy
        """
        top_cats: List[str] = self.get_top_categories()
        low_cats: List[str] = []
        for top_cat in top_cats:
            for mid_cat in self.get_mid_categories(top_cat):
                low_cats.extend(self.get_low_categories(top_cat, mid_cat))
        return low_cats

    def get_top_categories(self) -> List[str]:
        return list(self.taxonomy.keys())

    def get_mid_categories(self, top_category: str) -> List[str]:
        return list(self.taxonomy[top_category].keys())

    def get_low_categories(self, top_category: str, mid_category: str) -> List[str]:
        return self.taxonomy[top_category][mid_category]

    def get_top_cat_for_mid_cat(self, mid_cat: str) -> str:
        self.logger.info(f"Getting top category for mid category: {mid_cat}")

        top_cat: str = ""
        found: bool = False

        while not found:
            self.logger.info(
                f"Iterating through top_cat, mid_cat key value pairs in taxonomy"
            )
            for top_cat, mid_cats in self.taxonomy.items():
                self.logger.info(f"Checking mid category: {mid_cat} in {mid_cats}")
                if mid_cat in mid_cats:
                    self.logger.info(f"Mid category: {mid_cat} found in {mid_cats}")
                    found: bool = True
                    break
            self.logger.info(
                f"Completed iteration through top_cat, mid_cat key value pairs in taxonomy"
            )
            if found:
                break
        self.logger.info(f"Found top category: {top_cat} for mid category: {mid_cat}")
        return top_cat

    def get_mid_cat_for_low_cat(self, low_cat: str) -> str:
        self.logger.info(f"Getting mid category for low category: {low_cat}")

        mid_cat: str = ""
        found: bool = False
        while not found:
            self.logger.info(
                f"Iterating through top_cat, mid_cat, low_cat key value pairs in taxonomy"
            )
            for top_cat, mid_cats in self.taxonomy.items():
                for mid_cat, low_cats in mid_cats.items():
                    self.logger.info(f"Checking low category: {low_cat} in {low_cats}")
                    if low_cat in low_cats:
                        self.logger.info(f"Low category: {low_cat} found in {low_cats}")
                        found: bool = True
                        break
            self.logger.info(
                f"Completed iteration through top_cat, mid_cat, low_cat key value pairs in taxonomy"
            )
            if found:
                break
        self.logger.info(f"Found mid category: {mid_cat} for low category: {low_cat}")
        return mid_cat

    def is_valid_category(
        self, category: str, level: Literal["top", "mid", "low"]
    ) -> bool:
        """Validates if a category exists in the taxonomy at the specified level.

        Args:
            category: The category name to validate
            level: The taxonomy level ("top", "mid", or "low")

        Returns:
            bool: True if the category exists at the specified level, False otherwise
        """
        if level not in ["top", "mid", "low"]:
            raise ValueError(
                f"Invalid taxonomy level: {level}. Must be one of: 'top', 'mid', 'low'"
            )

        if level == "top":
            return category in self.all_top_categories
        elif level == "mid":
            return category in self.all_mid_categories
        elif level == "low":
            return category in self.all_low_categories

    def get_taxonomy(self) -> TaxonomyDict:
        return self.taxonomy

    @staticmethod
    def _load_taxonomy_from_string(
        taxonomy_str: str, logger: logging.Logger | None = None
    ) -> TaxonomyDict:
        if logger is not None:
            logger.info("Loading taxonomy from string")

        taxonomy: TaxonomyDict = json.loads(taxonomy_str)

        if logger is not None:
            logger.info("Taxonomy loaded successfully")

        return taxonomy


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
