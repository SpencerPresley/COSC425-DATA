import json
import logging
from typing import Dict, List, Literal, TypeAlias

from academic_metrics.configs import configure_logging, DEBUG
from academic_metrics.other.in_memory_taxonomy import TAXONOMY_AS_STRING

# Type Aliases
TaxonomyDict: TypeAlias = Dict[str, Dict[str, List[str]]]
"""Type alias representing the taxonomy dictionary structure.

This type represents a three-level nested dictionary structure where:
    - The outer dictionary maps top-level category names to mid-level dictionaries
    - The mid-level dictionaries map mid-level category names to lists of low-level categories
    - The innermost lists contain strings representing low-level category names

Type Structure:
    Dict[str, Dict[str, List[str]]] where:
        - First str: Top-level category name
        - Second str: Mid-level category name
        - List[str]: List of low-level category names

Example Structure:
    .. code-block:: python

        {
            "Computer Science": {                     # Top-level category
                "Artificial Intelligence": [          # Mid-level category
                    "Machine Learning",              # Low-level category
                    "Natural Language Processing",   # Low-level category
                    "Computer Vision"                # Low-level category
                ],
                "Software Engineering": [
                    "Software Design",
                    "Software Testing",
                    "DevOps"
                ]
            }
        }
"""

TaxonomyLevel: TypeAlias = Literal["top", "mid", "low"]
"""Type alias representing valid taxonomy levels.

This type represents the three possible levels in the taxonomy hierarchy using string literals.

Type Structure:
    Literal["top", "mid", "low"] where:
        - "top": Represents the highest level categories (e.g., "Computer Science")
        - "mid": Represents middle-level categories (e.g., "Artificial Intelligence")
        - "low": Represents the most specific categories (e.g., "Machine Learning")

Usage:
    .. code-block:: python

        def example_function(level: TaxonomyLevel) -> None:
            match level:
                case "top":
                    # Handle top-level category
                    pass
                case "mid":
                    # Handle mid-level category
                    pass
                case "low":
                    # Handle low-level category
                    pass

Note:
    The type system will ensure that only these three string literals can be used
    where a TaxonomyLevel is expected. Any other string will result in a type error.

Example:
    .. code-block:: python

        # Valid usage
        level: TaxonomyLevel = "top"      # OK
        level: TaxonomyLevel = "mid"      # OK
        level: TaxonomyLevel = "low"      # OK
        
        # Invalid usage (would cause type error)
        # level: TaxonomyLevel = "other"  # Type error!
"""


class Taxonomy:
    """A class for managing and querying a three-level taxonomy structure.

    This class provides functionality to work with a hierarchical taxonomy that has three levels:
    top, mid, and low. It allows for querying categories at each level, validating categories,
    and finding relationships between categories at different levels.

    Attributes:
        _taxonomy (TaxonomyDict): The complete taxonomy structure as a nested dictionary.
        _valid_levels (List[TaxonomyLevel]): List of valid taxonomy levels ["top", "mid", "low"].
        _all_top_categories (List[str]): Cached list of all top-level categories.
        _all_mid_categories (List[str]): Cached list of all mid-level categories.
        _all_low_categories (List[str]): Cached list of all low-level categories.
        logger (logging.Logger): Logger instance for this class.

    Methods:
        Public Methods:
            get_top_categories(): Get all top-level categories.
            get_mid_categories(top_category): Get mid-level categories for a top category.
            get_low_categories(top_category, mid_category): Get low-level categories.
            get_top_cat_for_mid_cat(mid_cat): Find parent top category of a mid category.
            get_mid_cat_for_low_cat(low_cat): Find parent mid category of a low category.
            is_valid_category(category, level): Check if a category exists at a level.
            get_taxonomy(): Get the complete taxonomy dictionary.

        Private Methods:
            _set_all_top_categories(): Initialize list of top categories.
            _set_all_mid_categories(): Initialize list of mid categories.
            _set_all_low_categories(): Initialize list of low categories.
            _load_taxonomy_from_string(taxonomy_str, logger): Load taxonomy from JSON.

    Examples:
        .. code-block:: python

            # Create a taxonomy instance
            taxonomy = Taxonomy()

            # Get categories at different levels
            top_cats = taxonomy.get_top_categories()
            mid_cats = taxonomy.get_mid_categories(top_cats[0])
            low_cats = taxonomy.get_low_categories(top_cats[0], mid_cats[0])

            # Validate categories
            taxonomy.is_valid_category(top_cats[0], "top")
            True

            # Find parent categories
            parent_top = taxonomy.get_top_cat_for_mid_cat(mid_cats[0])
            parent_mid = taxonomy.get_mid_cat_for_low_cat(low_cats[0])
    """

    def __init__(self) -> None:
        """Initializes a new Taxonomy instance.

        This constructor initializes the taxonomy by loading the taxonomy data from a predefined
        string constant (TAXONOMY_AS_STRING). It sets up logging and initializes internal lists
        of categories at all levels (top, mid, and low).

        The taxonomy follows a three-level hierarchical structure:
        - Top level: Broad categories
        - Mid level: Sub-categories under each top category
        - Low level: Specific categories under each mid category

        Examples:
            .. code-block:: python

                # Create a new taxonomy instance
                taxonomy = Taxonomy()
                isinstance(taxonomy._taxonomy, dict)
                True

                # Verify initialization of category lists
                all(isinstance(cats, list) for cats in [
                    taxonomy._all_top_categories,
                    taxonomy._all_mid_categories,
                    taxonomy._all_low_categories
                ])
                True

                # Check that valid levels are properly set
                taxonomy._valid_levels == ["top", "mid", "low"]
                True
        """
        self.logger = configure_logging(
            module_name=__name__,
            log_file_name="taxonomy_util",
            log_level=DEBUG,
        )

        self.logger.info("Initializing Taxonomy")
        self._taxonomy: TaxonomyDict = self._load_taxonomy_from_string(
            TAXONOMY_AS_STRING, self.logger
        )
        self.logger.info("Taxonomy initialized successfully")

        self._valid_levels: List[TaxonomyLevel] = ["top", "mid", "low"]
        self._all_top_categories: List[str] = self._set_all_top_categories()
        self._all_mid_categories: List[str] = self._set_all_mid_categories()
        self._all_low_categories: List[str] = self._set_all_low_categories()

    def __str__(self) -> str:
        """Returns a string representation of the taxonomy.

        Converts the taxonomy dictionary into a formatted JSON string with proper indentation.
        This method is useful for debugging and displaying the taxonomy structure.

        Returns:
            str: A JSON-formatted string representation of the taxonomy.

        Examples:
            .. code-block:: python

                taxonomy = Taxonomy()
                taxonomy_str = str(taxonomy)
                isinstance(taxonomy_str, str)
                True
                # Verify it's valid JSON
                json.loads(taxonomy_str) == taxonomy._taxonomy
                True
        """
        self.logger.info("Converting taxonomy to string")
        taxonomy_str: str = json.dumps(self._taxonomy, indent=4)
        self.logger.info("Taxonomy string converted successfully")
        return taxonomy_str

    def _set_all_top_categories(self) -> List[str]:
        """Sets and returns all top-level categories from the taxonomy.

        This private method initializes the list of all top-level categories
        by calling get_top_categories(). It's used during taxonomy initialization
        to cache the top-level categories for faster access.

        Returns:
            List[str]: A list of all top-level categories in the taxonomy.

        Examples:
            .. code-block:: python

                taxonomy = Taxonomy()
                top_cats = taxonomy._set_all_top_categories()
                isinstance(top_cats, list)
                True
                # Verify all elements are strings
                all(isinstance(cat, str) for cat in top_cats)
                True
                # Verify it matches direct access to top categories
                top_cats == taxonomy.get_top_categories()
                True
        """
        return self.get_top_categories()

    def _set_all_mid_categories(self) -> List[str]:
        """Sets and returns all mid-level categories from the taxonomy.

        This private method collects all mid-level categories across all top-level categories
        by iterating through the taxonomy structure. It's used during taxonomy initialization
        to cache the mid-level categories for faster access.

        Returns:
            List[str]: A list of all mid-level categories in the taxonomy.

        Examples:
            .. code-block:: python

                taxonomy = Taxonomy()
                mid_cats = taxonomy._set_all_mid_categories()
                isinstance(mid_cats, list)
                True
                # Verify all elements are strings
                all(isinstance(cat, str) for cat in mid_cats)
                True
                # Verify each mid category belongs to some top category
                any(mid_cats[0] in taxonomy.get_mid_categories(top_cat)
                    for top_cat in taxonomy.get_top_categories())
                True
        """
        top_cats: List[str] = self.get_top_categories()
        mid_cats: List[str] = []
        for top_cat in top_cats:
            mid_cats.extend(self.get_mid_categories(top_cat))
        return mid_cats

    def _set_all_low_categories(self) -> List[str]:
        """Sets and returns all low-level categories from the taxonomy.

        This private method collects all low-level categories by iterating through
        all top and mid-level categories in the taxonomy structure. It's used during
        taxonomy initialization to cache the low-level categories for faster access.

        Returns:
            List[str]: A list of all low-level categories in the taxonomy.

        Examples:
            .. code-block:: python

                taxonomy = Taxonomy()
                low_cats = taxonomy._set_all_low_categories()
                isinstance(low_cats, list)
                True
                # Verify all elements are strings
                all(isinstance(cat, str) for cat in low_cats)
                True
                # Verify first low category exists in taxonomy structure
                top_cat = taxonomy.get_top_categories()[0]
                mid_cat = taxonomy.get_mid_categories(top_cat)[0]
                low_cats[0] in taxonomy.get_low_categories(top_cat, mid_cat)
                True
        """
        top_cats: List[str] = self.get_top_categories()
        low_cats: List[str] = []
        for top_cat in top_cats:
            for mid_cat in self.get_mid_categories(top_cat):
                low_cats.extend(self.get_low_categories(top_cat, mid_cat))
        return low_cats

    def get_top_categories(self) -> List[str]:
        """Retrieves all top-level categories from the taxonomy.

        Returns:
            List[str]: A list of all top-level category names.

        Examples:
            .. code-block:: python

                taxonomy = Taxonomy()
                top_cats = taxonomy.get_top_categories()
                isinstance(top_cats, list)
                True
                # Verify all elements are strings
                all(isinstance(cat, str) for cat in top_cats)
                True
                # Verify returned list matches taxonomy keys
                top_cats == list(taxonomy._taxonomy.keys())
                True
        """
        return list(self._taxonomy.keys())

    def get_mid_categories(self, top_category: str) -> List[str]:
        """Retrieves all mid-level categories for a given top-level category.

        Args:
            top_category (str): The top-level category name to get mid-level categories for.

        Returns:
            List[str]: A list of all mid-level category names under the specified top category.

        Raises:
            KeyError: If the top_category doesn't exist in the taxonomy.

        Examples:
            .. code-block:: python

                taxonomy = Taxonomy()
                top_cat = taxonomy.get_top_categories()[0]
                mid_cats = taxonomy.get_mid_categories(top_cat)
                isinstance(mid_cats, list)
                True
                # Verify all elements are strings
                all(isinstance(cat, str) for cat in mid_cats)
                True
                # Verify error handling
                try:
                    taxonomy.get_mid_categories("nonexistent_category")
                except KeyError:
                    True
        """
        return list(self._taxonomy[top_category].keys())

    def get_low_categories(self, top_category: str, mid_category: str) -> List[str]:
        """Retrieves all low-level categories for given top and mid-level categories.

        Args:
            top_category (str): The top-level category name.
            mid_category (str): The mid-level category name under the top category.

        Returns:
            List[str]: A list of all low-level category names under the specified categories.

        Raises:
            KeyError: If either the top_category or mid_category doesn't exist in the taxonomy.

        Examples:
            .. code-block:: python

                taxonomy = Taxonomy()
                top_cat = taxonomy.get_top_categories()[0]
                mid_cat = taxonomy.get_mid_categories(top_cat)[0]
                low_cats = taxonomy.get_low_categories(top_cat, mid_cat)
                isinstance(low_cats, list)
                True
                # Verify all elements are strings
                all(isinstance(cat, str) for cat in low_cats)
                True
                # Verify error handling for invalid categories
                try:
                    taxonomy.get_low_categories("nonexistent", "category")
                except KeyError:
                    True
        """
        return self._taxonomy[top_category][mid_category]

    def get_top_cat_for_mid_cat(self, mid_cat: str) -> str:
        """Finds the top-level category that contains a given mid-level category.

        This method searches through the taxonomy structure to find which top-level category
        contains the given mid-level category name.

        Args:
            mid_cat (str): The mid-level category to find the parent for.

        Returns:
            str: The name of the top-level category containing the mid-level category.

        Raises:
            ValueError: If the mid_cat is not found in any top-level category.

        Example:
            .. code-block:: python
                from academic_metrics.utils import Taxonomy

                taxonomy = Taxonomy()
                # Get a known mid category and its top category
                top_cat = taxonomy.get_top_categories()[0]
                mid_cat = taxonomy.get_mid_categories(top_cat)[0]

                # Verify we can find the top category
                found_top = taxonomy.get_top_cat_for_mid_cat(mid_cat)
                assert found_top == top_cat

                # Verify error handling for invalid mid category
                try:
                    taxonomy.get_top_cat_for_mid_cat("nonexistent_category")
                except ValueError:
                    pass  # Expected behavior
        """
        self.logger.info(f"Getting top category for mid category: {mid_cat}")

        for top_cat, mid_cats in self._taxonomy.items():
            self.logger.info(f"Checking mid category: {mid_cat} in {mid_cats}")
            if mid_cat in mid_cats:
                self.logger.info(f"Mid category: {mid_cat} found in {mid_cats}")
                self.logger.info(
                    f"Found top category: {top_cat} for mid category: {mid_cat}"
                )
                return top_cat

        raise ValueError(f"Mid category '{mid_cat}' not found in taxonomy")

    def get_mid_cat_for_low_cat(self, low_cat: str) -> str:
        """Finds the mid-level category that contains a given low-level category.

        This method searches through the taxonomy structure to find which mid-level category
        contains the given low-level category name.

        Args:
            low_cat (str): The low-level category to find the parent for.

        Returns:
            str: The name of the mid-level category containing the low-level category.

        Raises:
            ValueError: If the low_cat is not found in any mid-level category.

        Examples:
            .. code-block:: python

                from academic_metrics.utils import Taxonomy

                taxonomy = Taxonomy()
                # Get a known low category and its parent categories
                top_cat = taxonomy.get_top_categories()[0]
                mid_cat = taxonomy.get_mid_categories(top_cat)[0]
                low_cat = taxonomy.get_low_categories(top_cat, mid_cat)[0]

                # Verify we can find the mid category
                found_mid = taxonomy.get_mid_cat_for_low_cat(low_cat)
                assert found_mid == mid_cat

                # Verify error handling for invalid low category
                try:
                    taxonomy.get_mid_cat_for_low_cat("nonexistent_category")
                except ValueError:
                    pass  # Expected behavior
        """
        self.logger.info(f"Getting mid category for low category: {low_cat}")

        for _, mid_cats in self._taxonomy.items():
            for mid_cat, low_cats in mid_cats.items():
                self.logger.info(f"Checking low category: {low_cat} in {low_cats}")
                if low_cat in low_cats:
                    self.logger.info(f"Low category: {low_cat} found in {low_cats}")
                    self.logger.info(
                        f"Found mid category: {mid_cat} for low category: {low_cat}"
                    )
                    return mid_cat

        # If we complete the loop without finding a match
        raise ValueError(f"Low category '{low_cat}' not found in taxonomy")

    def is_valid_category(self, category: str, level: TaxonomyLevel) -> bool:
        """Validates whether a category exists in the taxonomy at the specified level.

        Args:
            category (str): The name of the category to validate.
            level (TaxonomyLevel): The taxonomy level to validate against.
                TaxonomyLevel is a type alias for the taxonomy levels; it can be one of the following: "top", "mid", or "low".

        Returns:
            bool: True if the category exists at the specified level; otherwise, False.

        Raises:
            ValueError: If the provided taxonomy level is invalid.

        Examples:
            .. code-block:: python

                taxonomy = Taxonomy()
                # Get known categories at each level
                top_cat = taxonomy.get_top_categories()[0]
                mid_cat = taxonomy.get_mid_categories(top_cat)[0]
                low_cat = taxonomy.get_low_categories(top_cat, mid_cat)[0]

                # Test valid categories at each level
                taxonomy.is_valid_category(top_cat, "top")
                True
                taxonomy.is_valid_category(mid_cat, "mid")
                True
                taxonomy.is_valid_category(low_cat, "low")
                True

                # Test invalid categories
                taxonomy.is_valid_category("nonexistent_category", "top")
                False

                # Test category at wrong level
                taxonomy.is_valid_category(top_cat, "low")
                False

                # Test invalid level
                try:
                    taxonomy.is_valid_category(top_cat, "invalid_level")  # type: ignore
                except ValueError:
                    True
        """
        if level not in self._valid_levels:
            raise ValueError(
                f"Invalid taxonomy level: {level}. Must be one of: {self._valid_levels}"
            )

        attribute_name = f"_all_{level}_categories"
        return category in getattr(self, attribute_name)

    def get_taxonomy(self) -> TaxonomyDict:
        """Returns the complete taxonomy dictionary.

        Returns:
            TaxonomyDict: The complete taxonomy structure as a dictionary.

        Note:
            The structure follows the format:

            .. code-block:: python

                {
                    "top_category": {
                        "mid_category": ["low_category1", "low_category2", ...]
                    }
                }

        Examples:
            .. code-block:: python

                taxonomy = Taxonomy()
                tax_dict = taxonomy.get_taxonomy()
                isinstance(tax_dict, dict)
                True
                # Verify structure
                top_cat = list(tax_dict.keys())[0]
                isinstance(tax_dict[top_cat], dict)
                True
                mid_cat = list(tax_dict[top_cat].keys())[0]
                isinstance(tax_dict[top_cat][mid_cat], list)
                True
        """
        return self._taxonomy

    @staticmethod
    def _load_taxonomy_from_string(
        taxonomy_str: str, logger: logging.Logger | None = None
    ) -> TaxonomyDict:
        """Loads and parses a taxonomy from a JSON string.

        Args:
            taxonomy_str (str): JSON string containing the taxonomy structure.
            logger (logging.Logger | None, optional): Logger instance for logging operations.
                Defaults to None.

        Returns:
            TaxonomyDict: The parsed taxonomy dictionary.

        Raises:
            json.JSONDecodeError: If the taxonomy string is not valid JSON.

        Examples:
            .. code-block:: python

                # Create a simple valid taxonomy string
                tax_str = '{"top": {"mid": ["low1", "low2"]}}'
                taxonomy = Taxonomy._load_taxonomy_from_string(tax_str)
                isinstance(taxonomy, dict)
                True
                # Verify structure
                list(taxonomy.keys()) == ["top"]
                True
                # Test invalid JSON
                try:
                    Taxonomy._load_taxonomy_from_string("{invalid json}")
                except json.JSONDecodeError:
                    True
        """
        if logger is not None:
            logger.info("Loading taxonomy from string")

        taxonomy: TaxonomyDict = json.loads(taxonomy_str)

        if logger is not None:
            logger.info("Taxonomy loaded successfully")

        return taxonomy


def demo_taxonomy():
    """Demonstrates the basic functionality of the Taxonomy class."""
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


if __name__ == "__main__":
    import unittest
    import argparse

    parser = argparse.ArgumentParser(description="Taxonomy utility")
    parser.add_argument("--demo", action="store_true", help="Run the demo")

    args = parser.parse_args()

    class TestTaxonomy(unittest.TestCase):
        def setUp(self):
            self.taxonomy = Taxonomy()

        def test_get_top_categories(self):
            top_cats = self.taxonomy.get_top_categories()
            self.assertIsInstance(top_cats, list)
            self.assertTrue(all(isinstance(cat, str) for cat in top_cats))

        def test_get_mid_categories(self):
            top_cats = self.taxonomy.get_top_categories()
            for top_cat in top_cats:
                mid_cats = self.taxonomy.get_mid_categories(top_cat)
                self.assertIsInstance(mid_cats, list)
                self.assertTrue(all(isinstance(cat, str) for cat in mid_cats))

        def test_get_low_categories(self):
            top_cats = self.taxonomy.get_top_categories()
            for top_cat in top_cats:
                mid_cats = self.taxonomy.get_mid_categories(top_cat)
                for mid_cat in mid_cats:
                    low_cats = self.taxonomy.get_low_categories(top_cat, mid_cat)
                    self.assertIsInstance(low_cats, list)
                    self.assertTrue(all(isinstance(cat, str) for cat in low_cats))

        def test_is_valid_category(self):
            # Test invalid level
            with self.assertRaises(ValueError):
                self.taxonomy.is_valid_category("test", "invalid_level")

            # Test valid categories
            top_cat = self.taxonomy.get_top_categories()[0]
            self.assertTrue(self.taxonomy.is_valid_category(top_cat, "top"))

            mid_cat = self.taxonomy.get_mid_categories(top_cat)[0]
            self.assertTrue(self.taxonomy.is_valid_category(mid_cat, "mid"))

            low_cat = self.taxonomy.get_low_categories(top_cat, mid_cat)[0]
            self.assertTrue(self.taxonomy.is_valid_category(low_cat, "low"))

            # Test invalid category
            self.assertFalse(
                self.taxonomy.is_valid_category("nonexistent_category", "top")
            )

        def test_get_top_cat_for_mid_cat(self):
            top_cat = self.taxonomy.get_top_categories()[0]
            mid_cat = self.taxonomy.get_mid_categories(top_cat)[0]
            found_top_cat = self.taxonomy.get_top_cat_for_mid_cat(mid_cat)
            self.assertEqual(found_top_cat, top_cat)

        def test_get_mid_cat_for_low_cat(self):
            top_cat = self.taxonomy.get_top_categories()[0]
            mid_cat = self.taxonomy.get_mid_categories(top_cat)[0]
            low_cat = self.taxonomy.get_low_categories(top_cat, mid_cat)[0]
            found_mid_cat = self.taxonomy.get_mid_cat_for_low_cat(low_cat)
            self.assertEqual(found_mid_cat, mid_cat)

    # Run the tests
    unittest.main(argv=[""], exit=False)

    if args.demo:
        demo_taxonomy()
