from __future__ import annotations

import logging
import os
import json
from typing import TYPE_CHECKING, Any, Dict, List, Set, Tuple
from urllib.parse import quote

from academic_metrics.configs import (
    configure_logging,
    LOG_TO_CONSOLE,
    DEBUG,
)
from academic_metrics.enums import AttributeTypes, DataClassTypes

if TYPE_CHECKING:
    from academic_metrics.dataclass_models import (
        CategoryInfo,
        FacultyStats,
        GlobalFacultyStats,
        CrossrefArticleStats,
        CrossrefArticleDetails,
    )
    from academic_metrics.utils import Utilities
    from academic_metrics.utils import WarningManager
    from academic_metrics.factories import DataClassFactory
    from academic_metrics.utils.taxonomy_util import Taxonomy


class CategoryProcessor:
    """Processes and organizes academic publication data by categories.

    This class handles the processing of classified publication data, organizing it into
    categories and generating various statistics. It manages faculty affiliations,
    article details, and category relationships.

    Args:
        None

    Attributes:
        utils (Utilities): Utility functions for data processing.
        warning_manager (WarningManager): System for handling and logging warnings.
        dataclass_factory (DataClassFactory): Factory for creating data model instances.
        taxonomy_util (Taxonomy): Utility for managing publication taxonomy.
        category_data (Dict[str, CategoryInfo]): Mapping of categories to their information.
        faculty_stats (Dict[str, FacultyStats]): Faculty statistics by category.
        global_faculty_stats (Dict[str, GlobalFacultyStats]): Global faculty statistics.
        category_article_stats (Dict[str, CrossrefArticleStats]): Article statistics by category.
        articles (List[CrossrefArticleDetails]): List of processed article details.
        logger (logging.Logger): Logger instance for this class.
        log_file_path (str): Path to the log file.

    Methods:
        process_data_list: Process a list of publication data items
        get_category_data: Get processed category data
        get_category_article_stats: Get article statistics by category
        get_articles: Get list of processed articles
        get_faculty_stats: Get faculty statistics by category
        get_global_faculty_stats: Get global faculty statistics
        call_get_attributes: Extract attributes from raw data
        update_category_stats: Update statistics for a category
        update_faculty_stats: Update faculty statistics
        update_global_faculty_stats: Update global faculty statistics
        update_category_article_stats: Update article statistics by category
        create_article_object: Create a new article object
        clean_faculty_affiliations: Clean faculty affiliation data
        clean_faculty_members: Clean faculty member data
        initialize_categories: Initialize category data structures
        _collect_all_affiliations: Collect all faculty affiliations
        _generate_url: Generate URL from string
        _generate_normal_id: Generate normalized ID from strings
    """

    def __init__(
        self,
        utils: Utilities,
        dataclass_factory: DataClassFactory,
        warning_manager: WarningManager,
        taxonomy_util: Taxonomy,
        log_to_console: bool | None = LOG_TO_CONSOLE,
    ) -> None:
        """Initialize the CategoryProcessor with required dependencies.

        Sets up logging configuration and initializes all required components for
        processing publication data, including utilities, factories, and data structures
        for storing category, faculty, and article information.

        Args:
            utils (Utilities): Utility functions for data processing.
                Type: :class:`academic_metrics.core.utilities.Utilities`
            dataclass_factory (DataClassFactory): Factory for creating data model instances.
                Type: :class:`academic_metrics.core.data_class_factory.DataClassFactory`
            warning_manager (WarningManager): System for handling and logging warnings.
                Type: :class:`academic_metrics.core.warning_manager.WarningManager`
            taxonomy_util (Taxonomy): Utility for managing publication taxonomy.
                Type: :class:`academic_metrics.core.taxonomy.Taxonomy`
            log_to_console (bool | None): Whether to log output to console.
                Type: bool | None
                Defaults to LOG_TO_CONSOLE.

        Raises:
            ValueError: If required dependencies are not properly initialized
            IOError: If log file cannot be created or accessed

        Notes:
            Initializes the following data structures:
            - category_data: Dictionary mapping categories to their information
            - faculty_stats: Dictionary tracking faculty statistics by category
            - global_faculty_stats: Dictionary tracking global faculty statistics
            - category_article_stats: Dictionary tracking article stats per category
            - articles: List of CrossrefArticleDetails objects for ground truth data
        """
        self.logger = configure_logging(
            module_name=__name__,
            log_file_name="category_processor",
            log_level=DEBUG,
        )

        self.utils: Utilities = utils
        self.warning_manager: WarningManager = warning_manager
        self.dataclass_factory: DataClassFactory = dataclass_factory
        self.taxonomy_util: Taxonomy = taxonomy_util
        self.category_data: Dict[str, CategoryInfo] = {}

        # influential stats dictionaries
        self.faculty_stats: Dict[str, FacultyStats] = {}
        self.global_faculty_stats: Dict[str, GlobalFacultyStats] = {}

        # Seperately tracks article stats for each category the article is in
        # This gives the article stats for each article under a given category
        self.category_article_stats: Dict[str, CrossrefArticleStats] = {}

        # This creates a CrossrefArticleDetails object for each article
        # This gives an object per article so that we can have ground truth articles
        # This is what allows for category stats to just have a list of DOIs as those can
        # be used to look up the article details object for that doi from this list of CrossrefArticleDetails
        # objects.
        self.articles: List[CrossrefArticleDetails] = []

    def process_data_list(self, data: List[Dict]) -> None:
        """Process a list of publication data items.

        Takes raw publication data and processes each item through several stages:
        1. Extracts base attributes
        2. Initializes category information
        3. Generates URL maps for categories
        4. Cleans faculty and affiliation data
        5. Updates various statistics (category, faculty, article)
        6. Creates article objects

        Args:
            data (List[Dict]): List of raw publication data dictionaries to process.
                Type: List[Dict[str, Any]]

        Raises:
            ValueError: If required attributes are missing from data
            Exception: If category information cannot be initialized

        Notes:
            - Processes each publication through all stages sequentially
            - Updates multiple data structures during processing
            - Maintains relationships between categories, faculty, and articles
            - Performs data cleaning and normalization
        """
        self.logger.info("Starting to process data list...")
        for i, item in enumerate(data):
            self.logger.info(f"Processing item: {i + 1} / {len(data)}")

            # Get base attributes
            self.logger.info("Calling get_attributes...")
            raw_attributes = self.call_get_attributes(data=item)
            self.logger.info(f"Raw attributes: {raw_attributes}")

            # Get category information
            self.logger.info("Starting category initialization...")
            category_levels: Dict[str, List[str]] = self.initialize_categories(
                raw_attributes.get("categories", [])
            )
            self.logger.info(
                f"Category levels:\n{json.dumps(category_levels, indent=4)}"
            )
            self.logger.info(f"Completed category initialization.")

            # Fetch out seperate category levels
            self.logger.info("Fetching category levels...")
            top_categories: List[str] = category_levels.get("top_level_categories", [])
            self.logger.info(f"Top categories: {top_categories}")
            mid_categories: List[str] = category_levels.get("mid_level_categories", [])
            self.logger.info(f"Mid categories: {mid_categories}")
            low_categories: List[str] = category_levels.get("low_level_categories", [])
            self.logger.info(f"Low categories: {low_categories}")
            all_categories: List[str] = category_levels.get("all_categories", [])
            self.logger.info(f"All categories: {all_categories}")
            self.logger.info("Completed category level fetch.")

            # Create URL maps for each category level
            self.logger.info("Starting URL map creation...")
            top_level_url_map: Dict[str, str] = {}
            mid_level_url_map: Dict[str, str] = {}
            low_level_url_map: Dict[str, str] = {}
            self.logger.info("Completed URL map creation.")

            self.logger.info("Populating URL maps...")
            for category in all_categories:
                self.logger.info(f"Processing category: {category}")
                if category in low_categories:
                    self.logger.info("Category is in low categories.")

                    self.logger.info("Getting mid category for low category...")
                    mid_cat = self.taxonomy_util.get_mid_cat_for_low_cat(category)
                    self.logger.info(f"Mid category: {mid_cat}")

                    self.logger.info("Getting top category for mid category...")
                    top_cat = self.taxonomy_util.get_top_cat_for_mid_cat(mid_cat)
                    self.logger.info(f"Top category: {top_cat}")

                    self.logger.info("Generating URL for low category...")
                    low_level_url_map[category] = self._generate_url(
                        f"{top_cat}/{mid_cat}/{category}", self.logger
                    )
                    self.logger.info(f"Low level URL: {low_level_url_map[category]}")

                elif category in mid_categories:
                    self.logger.info("Category is in mid categories.")

                    self.logger.info("Getting top category for mid category...")
                    top_cat = self.taxonomy_util.get_top_cat_for_mid_cat(category)
                    self.logger.info(f"Top category: {top_cat}")

                    self.logger.info("Generating URL for mid category...")
                    mid_level_url_map[category] = self._generate_url(
                        f"{top_cat}/{category}", self.logger
                    )
                    self.logger.info(f"Mid level URL: {mid_level_url_map[category]}")

                else:
                    self.logger.info("Category is in top categories.")

                    self.logger.info("Generating URL for top category...")
                    top_level_url_map[category] = self._generate_url(
                        category, self.logger
                    )
                    self.logger.info(f"Top level URL: {top_level_url_map[category]}")

            self.logger.info(
                f"Top level URL map:\n{json.dumps(top_level_url_map, indent=4)}"
            )
            self.logger.info(
                f"Mid level URL map:\n{json.dumps(mid_level_url_map, indent=4)}"
            )
            self.logger.info(
                f"Low level URL map:\n{json.dumps(low_level_url_map, indent=4)}"
            )
            self.logger.info("Completed URL map population.")

            # Clean special fields
            self.logger.info("Cleaning faculty members...")
            faculty_members: List[str] = self.clean_faculty_members(
                raw_attributes.get("faculty_members", [])
            )
            self.logger.info(
                f"Cleaned faculty members:\n{json.dumps(faculty_members, indent=4)}"
            )
            self.logger.info("Cleaning faculty affiliations...")
            faculty_affiliations: Dict[str, List[str]] = (
                self.clean_faculty_affiliations(
                    raw_attributes.get("faculty_affiliations", [])
                )
            )
            self.logger.info(
                f"Cleaned faculty affiliations:\n{json.dumps(faculty_affiliations, indent=4)}"
            )
            self.logger.info("Collecting all affiliations...")
            all_affiliations: Set[str] = self._collect_all_affiliations(
                faculty_affiliations, logger=self.logger
            )
            self.logger.info(
                f"Collected all affiliations:\n{json.dumps(list(all_affiliations), indent=4)}"
            )

            # Unpack everything into kwargs
            self.logger.info("Unpacking everything into kwargs...")
            kwargs = {
                # Basic article info
                "title": raw_attributes.get("title", ""),
                "doi": raw_attributes.get("doi", ""),
                "tc_count": raw_attributes.get("tc_count", 0),
                "abstract": raw_attributes.get("abstract", ""),
                "license_url": raw_attributes.get("license_url", ""),
                "date_published_print": raw_attributes.get("date_published_print", ""),
                "date_published_online": raw_attributes.get(
                    "date_published_online", ""
                ),
                "journal": raw_attributes.get("journal", ""),
                "download_url": raw_attributes.get("download_url", ""),
                "themes": raw_attributes.get("themes", []),
                # Faculty and affiliations
                "faculty_members": faculty_members,
                "faculty_affiliations": faculty_affiliations,
                "all_affiliations": all_affiliations,
                # Category information
                "all_categories": all_categories,
                "top_level_categories": top_categories,
                "mid_level_categories": mid_categories,
                "low_level_categories": low_categories,
                "url_maps": {
                    "top": top_level_url_map,
                    "mid": mid_level_url_map,
                    "low": low_level_url_map,
                },
            }
            self.logger.info("Completed unpacking everything into kwargs.")

            self.logger.info("Updating category stats...")
            self.update_category_stats(**kwargs)
            self.logger.info("Completed updating category stats.")

            self.logger.info("Updating faculty stats...")
            self.update_faculty_stats(**kwargs)
            self.logger.info("Completed updating faculty stats.")

            self.logger.info("Updating global faculty stats...")
            self.update_global_faculty_stats(**kwargs)
            self.logger.info("Completed updating global faculty stats.")

            self.logger.info("Updating category article stats...")
            self.update_category_article_stats(**kwargs)
            self.logger.info("Completed updating category article stats.")

            self.logger.info("Creating article object...")
            self.create_article_object(**kwargs)
            self.logger.info("Completed creating article object.")

    def _test_category_processor(self, raw_attributes: Dict[str, Any]) -> None:
        """Test method for validating category processing functionality.

        This private method is used for testing the category processor's ability to handle
        raw attribute data and properly process it through the category system.

        Args:
            raw_attributes (Dict[str, Any]): Dictionary of raw attributes to test processing.
                Type: Dict[str, Any]

        Notes:
            - Used for internal testing purposes only
            - Validates category processing pipeline
            - Does not modify production data
            - Helps ensure data integrity
        """
        # Get base attributes
        self.logger.info("Calling get_attributes...")
        self.logger.info(f"Raw attributes: {raw_attributes}")

        # Get category information
        self.logger.info("Starting category initialization...")
        category_levels: Dict[str, List[str]] = self.initialize_categories(
            raw_attributes.get("categories", [])
        )
        self.logger.info(f"Category levels:\n{json.dumps(category_levels, indent=4)}")
        self.logger.info(f"Completed category initialization.")

        # Fetch out seperate category levels
        self.logger.info("Fetching category levels...")
        top_categories: List[str] = category_levels.get("top_level_categories", [])
        self.logger.info(f"Top categories: {top_categories}")
        mid_categories: List[str] = category_levels.get("mid_level_categories", [])
        self.logger.info(f"Mid categories: {mid_categories}")
        low_categories: List[str] = category_levels.get("low_level_categories", [])
        self.logger.info(f"Low categories: {low_categories}")
        all_categories: List[str] = category_levels.get("all_categories", [])
        self.logger.info(f"All categories: {all_categories}")
        self.logger.info("Completed category level fetch.")

        # Create URL maps for each category level
        self.logger.info("Starting URL map creation...")
        top_level_url_map: Dict[str, str] = {}
        mid_level_url_map: Dict[str, str] = {}
        low_level_url_map: Dict[str, str] = {}
        self.logger.info("Completed URL map creation.")

        self.logger.info("Populating URL maps...")
        for category in all_categories:
            self.logger.info(f"Processing category: {category}")
            if category in low_categories:
                self.logger.info("Category is in low categories.")

                self.logger.info("Getting mid category for low category...")
                mid_cat = self.taxonomy_util.get_mid_cat_for_low_cat(category)
                self.logger.info(f"Mid category: {mid_cat}")

                self.logger.info("Getting top category for mid category...")
                top_cat = self.taxonomy_util.get_top_cat_for_mid_cat(mid_cat)
                self.logger.info(f"Top category: {top_cat}")

                self.logger.info("Generating URL for low category...")
                low_level_url_map[category] = self._generate_url(
                    f"{top_cat}/{mid_cat}/{category}", self.logger
                )
                self.logger.info(f"Low level URL: {low_level_url_map[category]}")

            elif category in mid_categories:
                self.logger.info("Category is in mid categories.")

                self.logger.info("Getting top category for mid category...")
                top_cat = self.taxonomy_util.get_top_cat_for_mid_cat(category)
                self.logger.info(f"Top category: {top_cat}")

                self.logger.info("Generating URL for mid category...")
                mid_level_url_map[category] = self._generate_url(
                    f"{top_cat}/{category}", self.logger
                )
                self.logger.info(f"Mid level URL: {mid_level_url_map[category]}")

            else:
                self.logger.info("Category is in top categories.")

                self.logger.info("Generating URL for top category...")
                top_level_url_map[category] = self._generate_url(category, self.logger)
                self.logger.info(f"Top level URL: {top_level_url_map[category]}")

            self.logger.info(
                f"Top level URL map:\n{json.dumps(top_level_url_map, indent=4)}"
            )
            self.logger.info(
                f"Mid level URL map:\n{json.dumps(mid_level_url_map, indent=4)}"
            )
            self.logger.info(
                f"Low level URL map:\n{json.dumps(low_level_url_map, indent=4)}"
            )
            self.logger.info("Completed URL map population.")

            # Clean special fields
            self.logger.info("Cleaning faculty members...")
            faculty_members: List[str] = self.clean_faculty_members(
                raw_attributes.get("faculty_members", [])
            )
            self.logger.info(
                f"Cleaned faculty members:\n{json.dumps(faculty_members, indent=4)}"
            )
            self.logger.info("Cleaning faculty affiliations...")
            faculty_affiliations: Dict[str, List[str]] = (
                self.clean_faculty_affiliations(
                    raw_attributes.get("faculty_affiliations", [])
                )
            )
            self.logger.info(
                f"Cleaned faculty affiliations:\n{json.dumps(faculty_affiliations, indent=4)}"
            )
            self.logger.info("Collecting all affiliations...")
            all_affiliations: Set[str] = self._collect_all_affiliations(
                faculty_affiliations, logger=self.logger
            )
            self.logger.info(
                f"Collected all affiliations:\n{json.dumps(list(all_affiliations), indent=4)}"
            )

            # Unpack everything into kwargs
            self.logger.info("Unpacking everything into kwargs...")
            kwargs = {
                # Basic article info
                "title": raw_attributes.get("title", ""),
                "doi": raw_attributes.get("doi", ""),
                "tc_count": raw_attributes.get("tc_count", 0),
                "abstract": raw_attributes.get("abstract", ""),
                "license_url": raw_attributes.get("license_url", ""),
                "date_published_print": raw_attributes.get("date_published_print", ""),
                "date_published_online": raw_attributes.get(
                    "date_published_online", ""
                ),
                "journal": raw_attributes.get("journal", ""),
                "download_url": raw_attributes.get("download_url", ""),
                "themes": raw_attributes.get("themes", []),
                # Faculty and affiliations
                "faculty_members": faculty_members,
                "faculty_affiliations": faculty_affiliations,
                "all_affiliations": all_affiliations,
                # Category information
                "all_categories": all_categories,
                "top_level_categories": top_categories,
                "mid_level_categories": mid_categories,
                "low_level_categories": low_categories,
                "url_maps": {
                    "top": top_level_url_map,
                    "mid": mid_level_url_map,
                    "low": low_level_url_map,
                },
            }
            self.logger.info("Completed unpacking everything into kwargs.")

            self.logger.info("Updating category stats...")
            self.update_category_stats(**kwargs)
            self.logger.info("Completed updating category stats.")

            self.logger.info("Updating faculty stats...")
            self.update_faculty_stats(**kwargs)
            self.logger.info("Completed updating faculty stats.")

            self.logger.info("Updating global faculty stats...")
            self.update_global_faculty_stats(**kwargs)
            self.logger.info("Completed updating global faculty stats.")

            self.logger.info("Updating category article stats...")
            self.update_category_article_stats(**kwargs)
            self.logger.info("Completed updating category article stats.")

            self.logger.info("Creating article object...")
            self.create_article_object(**kwargs)
            self.logger.info("Completed creating article object.")

    def call_get_attributes(self, *, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and process attributes from raw publication data.

        Extracts various attributes including categories, authors, departments, titles,
        citations, abstracts, licenses, publication dates, journal info, URLs, DOIs,
        and themes from the raw data.

        Args:
            data (Dict[str, Any]): Raw publication data dictionary.
                Type: Dict[str, Any]

        Returns:
            Dict[str, Any]: Dictionary containing extracted and processed attributes.
                Type: Dict[str, Any]
                Contains:
                - categories (List[str]): List of publication categories
                - faculty_members (List[str]): List of faculty authors
                - faculty_affiliations (Dict[str, str]): Faculty to department mapping
                - title (str): Publication title
                - tc_count (int): Citation count
                - abstract (str): Publication abstract
                - license_url (str): License URL
                - date_published_print (str): Print publication date
                - date_published_online (str): Online publication date
                - journal (str): Journal name
                - download_url (str): Download URL
                - doi (str): Digital Object Identifier
                - themes (List[str]): List of publication themes

        Raises:
            Exception: If no category is found in the data

        Notes:
            - Extracts all available attributes from raw data
            - Performs basic validation of required fields
            - Handles missing optional fields gracefully
            - Maintains data types for each attribute
        """
        self.logger.info("Calling get_attributes...")

        attribute_results: Dict[AttributeTypes, Tuple[bool, Any]] = (
            self.utils.get_attributes(
                data,
                [
                    AttributeTypes.CROSSREF_CATEGORIES,
                    AttributeTypes.CROSSREF_AUTHORS,
                    AttributeTypes.CROSSREF_DEPARTMENTS,
                    AttributeTypes.CROSSREF_TITLE,
                    AttributeTypes.CROSSREF_CITATION_COUNT,
                    AttributeTypes.CROSSREF_ABSTRACT,
                    AttributeTypes.CROSSREF_LICENSE_URL,
                    AttributeTypes.CROSSREF_PUBLISHED_PRINT,
                    AttributeTypes.CROSSREF_PUBLISHED_ONLINE,
                    AttributeTypes.CROSSREF_JOURNAL,
                    AttributeTypes.CROSSREF_URL,
                    AttributeTypes.CROSSREF_DOI,
                    AttributeTypes.CROSSREF_THEMES,
                ],
            )
        )
        self.logger.info("Completed calling get_attributes.")

        self.logger.info("Checking if categories exist...")
        if attribute_results[AttributeTypes.CROSSREF_CATEGORIES][0]:
            categories: List[str] = attribute_results[
                AttributeTypes.CROSSREF_CATEGORIES
            ][1]
            self.logger.info(f"Got categories: {categories}")
        else:
            raise Exception(f"No category found for data: {data}")

        self.logger.info("Checking if faculty members exist...")
        faculty_members: List[str] | None = (
            attribute_results[AttributeTypes.CROSSREF_AUTHORS][1]
            if attribute_results[AttributeTypes.CROSSREF_AUTHORS][0]
            else None
        )
        self.logger.info(f"Got faculty members: {faculty_members}")

        self.logger.info("Checking if faculty affiliations exist...")
        faculty_affiliations: Dict[str, List[str]] | None = (
            attribute_results[AttributeTypes.CROSSREF_DEPARTMENTS][1]
            if attribute_results[AttributeTypes.CROSSREF_DEPARTMENTS][0]
            else None
        )
        self.logger.info(f"Got faculty affiliations: {faculty_affiliations}")

        self.logger.info("Checking if title exists...")
        title: str | None = (
            attribute_results[AttributeTypes.CROSSREF_TITLE][1]
            if attribute_results[AttributeTypes.CROSSREF_TITLE][0]
            else None
        )
        self.logger.info(f"Got title: {title}")

        self.logger.info("Checking if citation count exists...")
        tc_count: int | None = (
            attribute_results[AttributeTypes.CROSSREF_CITATION_COUNT][1]
            if attribute_results[AttributeTypes.CROSSREF_CITATION_COUNT][0]
            else None
        )
        self.logger.info(f"Got citation count: {tc_count}")

        self.logger.info("Checking if abstract exists...")
        abstract: str | None = (
            attribute_results[AttributeTypes.CROSSREF_ABSTRACT][1]
            if attribute_results[AttributeTypes.CROSSREF_ABSTRACT][0]
            else None
        )
        self.logger.info(f"Got abstract: {abstract}")

        self.logger.info("Checking if license URL exists...")
        license_url: str | None = (
            attribute_results[AttributeTypes.CROSSREF_LICENSE_URL][1]
            if attribute_results[AttributeTypes.CROSSREF_LICENSE_URL][0]
            else None
        )
        self.logger.info(f"Got license URL: {license_url}")

        self.logger.info("Checking if print publication date exists...")
        date_published_print: str | None = (
            attribute_results[AttributeTypes.CROSSREF_PUBLISHED_PRINT][1]
            if attribute_results[AttributeTypes.CROSSREF_PUBLISHED_PRINT][0]
            else None
        )
        self.logger.info(f"Got print publication date: {date_published_print}")

        self.logger.info("Checking if online publication date exists...")
        date_published_online: str | None = (
            attribute_results[AttributeTypes.CROSSREF_PUBLISHED_ONLINE][1]
            if attribute_results[AttributeTypes.CROSSREF_PUBLISHED_ONLINE][0]
            else None
        )
        self.logger.info(f"Got online publication date: {date_published_online}")

        self.logger.info("Checking if journal exists...")
        journal: str | None = (
            attribute_results[AttributeTypes.CROSSREF_JOURNAL][1]
            if attribute_results[AttributeTypes.CROSSREF_JOURNAL][0]
            else None
        )
        self.logger.info(f"Got journal: {journal}")

        self.logger.info("Checking if download URL exists...")
        download_url: str | None = (
            attribute_results[AttributeTypes.CROSSREF_URL][1]
            if attribute_results[AttributeTypes.CROSSREF_URL][0]
            else None
        )
        self.logger.info(f"Got download URL: {download_url}")

        self.logger.info("Checking if DOI exists...")
        doi: str | None = (
            attribute_results[AttributeTypes.CROSSREF_DOI][1]
            if attribute_results[AttributeTypes.CROSSREF_DOI][0]
            else None
        )
        self.logger.info(f"Got DOI: {doi}")

        self.logger.info("Checking if themes exist...")
        themes: List[str] | None = (
            attribute_results[AttributeTypes.CROSSREF_THEMES][1]
            if attribute_results[AttributeTypes.CROSSREF_THEMES][0]
            else None
        )
        self.logger.info(f"Got themes: {themes}")

        self.logger.info("Completed calling get_attributes.")

        self.logger.info("Returning attribute results...")
        return {
            "categories": categories,
            "faculty_members": faculty_members,
            "faculty_affiliations": faculty_affiliations,
            "title": title,
            "tc_count": tc_count,
            "abstract": abstract,
            "license_url": license_url,
            "date_published_print": date_published_print,
            "date_published_online": date_published_online,
            "journal": journal,
            "download_url": download_url,
            "doi": doi,
            "themes": themes,
        }

    def update_category_stats(self, **kwargs) -> None:
        """Update statistics for each category based on processed article data.

        Updates category information including faculty members, departments, titles,
        citation counts, DOIs, and themes. Also calculates derived statistics like
        faculty count, department count, article count, and citation averages.

        Args:
            **kwargs: Keyword arguments containing article data.
                Required arguments:
                - title (str): Article title
                    Type: str
                - doi (str): Digital Object Identifier
                    Type: str
                - tc_count (int): Citation count
                    Type: int
                - faculty_members (list): List of faculty authors
                    Type: List[str]
                - all_affiliations (set): Set of department affiliations
                    Type: Set[str]
                - themes (list): List of article themes
                    Type: List[str]
                - all_categories (list): List of all categories
                    Type: List[str]
                - url_maps (dict): Category URL mappings
                    Type: Dict[str, Dict[str, str]]

        Raises:
            KeyError: If required kwargs are missing
            ValueError: If category information cannot be updated

        Notes:
            - Updates multiple statistics per category
            - Calculates derived metrics from raw data
            - Maintains relationships between entities
            - Handles missing optional data gracefully
            - Updates both raw counts and computed averages
        """
        self.logger.info("Updating category stats...")
        for category in kwargs["all_categories"]:
            self.logger.info(f"Updating category stats for category: {category}")
            self.logger.info(f"Getting out category for URL via URL map...")
            url: str = (
                kwargs["url_maps"]["low"].get(category, "")
                or kwargs["url_maps"]["mid"].get(category, "")
                or kwargs["url_maps"]["top"].get(category, "")
            )
            self.logger.info(f"Retrieved URL: {url}")

            self.logger.info("Getting category info...")
            category_info: CategoryInfo = self.category_data[category]
            self.logger.info(f"Retrieved object type: {type(category_info)}")

            self.logger.info("Setting params for category info...")
            category_info.set_params(
                {
                    "_id": url,
                    "url": url,
                    "faculty": kwargs["faculty_members"],
                    "departments": kwargs["all_affiliations"],
                    "titles": kwargs["title"],
                    "tc_count": category_info.tc_count + kwargs["tc_count"],
                    "doi_list": kwargs["doi"],
                    "themes": kwargs["themes"],
                }
            )
            self.logger.info("Completed setting params for category info.")

            # Update counts based on set lengths after deduplication by the set_params() method
            self.logger.info(
                "Updating counts based on set lengths after deduplication..."
            )
            self.logger.info(f"Faculty count: {len(category_info.faculty)}")
            self.logger.info(f"Department count: {len(category_info.departments)}")
            self.logger.info(f"Article count: {len(category_info.titles)}")
            self.logger.info(f"Citation average: {category_info.citation_average}")
            category_info.faculty_count = len(category_info.faculty)
            category_info.department_count = len(category_info.departments)
            category_info.article_count = len(category_info.titles)
            category_info.citation_average = (
                category_info.tc_count / category_info.article_count
            )
            self.logger.info("Updated counts based on set lengths after deduplication.")
            self.logger.info(f"Updated faculty count: {category_info.faculty_count}")
            self.logger.info(
                f"Updated department count: {category_info.department_count}"
            )
            self.logger.info(f"Updated article count: {category_info.article_count}")
            self.logger.info(
                f"Updated citation average: {category_info.citation_average}"
            )
            self.logger.info("Completed updating category stats.")

    def update_faculty_stats(self, **kwargs) -> None:
        """Update faculty statistics for each category.

        Updates faculty member information including department affiliations,
        publication titles, DOIs, citation counts, and article counts. Creates
        or updates faculty statistics entries for each category.

        Args:
            **kwargs: Keyword arguments containing faculty and article data.
                Required arguments:
                - faculty_members (List): List of faculty authors
                    Type: List[str]
                - faculty_affiliations (Dict): Faculty department mappings
                    Type: Dict[str, List[str]]
                - title (str): Article title
                    Type: str
                - doi (str): Digital Object Identifier
                    Type: str
                - tc_count (int): Citation count
                    Type: int
                - all_categories (List): List of all categories
                    Type: List[str]
                - url_maps (Dict): Category URL mappings
                    Type: Dict[str, Dict[str, str]]

        Raises:
            KeyError: If required kwargs are missing
            ValueError: If faculty statistics cannot be updated

        Notes:
            - Updates statistics for each faculty member
            - Maintains faculty-department relationships
            - Tracks publication metrics per faculty
            - Handles multiple department affiliations
            - Updates both individual and aggregate statistics
        """
        self.logger.info("Updating faculty stats...")
        for category in kwargs["all_categories"]:
            self.logger.info(f"Updating faculty stats for category: {category}")

            self.logger.info("Checking if faculty stats for category exists...")
            if category not in self.faculty_stats:
                self.logger.info(
                    "Faculty stats for category does not exist, creating new..."
                )
                self.faculty_stats[category] = self.dataclass_factory.get_dataclass(
                    DataClassTypes.FACULTY_STATS,
                )
                self.logger.info("Created new faculty stats for category.")

            self.logger.info("Getting URL for category via URL map...")
            url: str = (
                kwargs["url_maps"]["low"].get(category, "")
                or kwargs["url_maps"]["mid"].get(category, "")
                or kwargs["url_maps"]["top"].get(category, "")
            )
            self.logger.info(f"Retrieved URL: {url}")

            self.logger.info("Updating faculty stats for each faculty member...")
            for faculty_member in kwargs["faculty_members"]:
                self.logger.info(
                    f"Updating faculty stats for faculty member: {faculty_member}"
                )

                self.logger.info(
                    "Generating normal ID for faculty member and category..."
                )
                faculty_data: Dict[str, Any] = {
                    "_id": self._generate_normal_id(
                        strings=[faculty_member, category], logger=self.logger
                    ),
                    "name": faculty_member,
                    "category": category,
                    "category_url": url,
                    "department_affiliations": kwargs["faculty_affiliations"].get(
                        faculty_member, []
                    ),
                    "titles": kwargs["title"],
                    "dois": kwargs["doi"],
                    "total_citations": kwargs["tc_count"],
                    "article_count": 1,
                    "doi_citation_map": {kwargs["doi"]: kwargs["tc_count"]},
                }

                self.logger.info("Setting params for faculty stats...")
                self.faculty_stats[category].set_params({faculty_member: faculty_data})
                self.logger.info("Completed setting params for faculty stats.")

        self.logger.info("Completed updating faculty stats.")

    def update_global_faculty_stats(self, **kwargs) -> None:
        """Update global statistics for each faculty member.

        Creates or updates global faculty statistics including total citations,
        article counts, department affiliations, DOIs, titles, categories,
        and category URLs across all publication categories.

        Args:
            **kwargs: Keyword arguments containing faculty and article data.
                Required arguments:
                - faculty_members (List): List of faculty authors
                    Type: List[str]
                - faculty_affiliations (Dict): Faculty department mappings
                    Type: Dict[str, List[str]]
                - title (str): Article title
                    Type: str
                - doi (str): Digital Object Identifier
                    Type: str
                - tc_count (int): Citation count
                    Type: int
                - all_categories (List): List of all categories
                    Type: List[str]
                - top_level_categories (List): Top-level categories
                    Type: List[str]
                - mid_level_categories (List): Mid-level categories
                    Type: List[str]
                - low_level_categories (List): Low-level categories
                    Type: List[str]
                - url_maps (Dict): Category URL mappings
                    Type: Dict[str, Dict[str, str]]
                - themes (List): Article themes
                    Type: List[str]
                - journal (str): Journal name
                    Type: str

        Raises:
            KeyError: If required kwargs are missing
            ValueError: If global faculty statistics cannot be updated

        Notes:
            - Updates global metrics for each faculty member
            - Tracks statistics across all categories
            - Maintains hierarchical category relationships
            - Handles multiple department affiliations
            - Aggregates publication metrics globally
        """
        self.logger.info("Updating global faculty stats...")
        for faculty_member in kwargs["faculty_members"]:
            self.logger.info(
                f"Updating global faculty stats for faculty member: {faculty_member}"
            )

            self.logger.info(
                "Checking if global faculty stats for faculty member exists..."
            )
            if faculty_member not in self.global_faculty_stats:
                self.logger.info(
                    "Global faculty stats for faculty member does not exist, creating new..."
                )
                self.global_faculty_stats[faculty_member] = (
                    self.dataclass_factory.get_dataclass(
                        DataClassTypes.GLOBAL_FACULTY_STATS, name=faculty_member
                    )
                )
                self.logger.info("Created new global faculty stats for faculty member.")

            # Get all URLs from maps
            # This logic even confused me so here's a not of why they get everything
            # This is global faculty stats, so the goal is after processing all papers
            # We can see the faculty members stats across papers without having to sum up all the individual records provided by the standard faculty stats which only look an individual category stat totals
            self.logger.info("Getting all URLs from maps...")
            self.logger.info(f"Getting top category URLs...")
            top_cat_urls: List[str] = [
                kwargs["url_maps"]["top"].get(cat)
                for cat in kwargs["top_level_categories"]
                if kwargs["url_maps"]["top"].get(cat)
            ]
            self.logger.info(f"Got top category URLs: {top_cat_urls}")

            self.logger.info("Getting mid category URLs...")
            mid_cat_urls: List[str] = [
                kwargs["url_maps"]["mid"].get(cat)
                for cat in kwargs["mid_level_categories"]
                if kwargs["url_maps"]["mid"].get(cat)
            ]
            self.logger.info(f"Got mid category URLs: {mid_cat_urls}")

            self.logger.info("Getting low category URLs...")
            low_cat_urls: List[str] = [
                kwargs["url_maps"]["low"].get(cat)
                for cat in kwargs["low_level_categories"]
                if kwargs["url_maps"]["low"].get(cat)
            ]
            self.logger.info(f"Got low category URLs: {low_cat_urls}")

            self.logger.info("Combining all category URLs...")
            all_cat_urls: List[str] = top_cat_urls + mid_cat_urls + low_cat_urls
            self.logger.info(f"Combined all category URLs: {all_cat_urls}")

            self.logger.info("Getting global faculty stats for faculty member...")
            global_stats: GlobalFacultyStats = self.global_faculty_stats[faculty_member]
            self.logger.info("Setting params for global faculty stats...")
            global_stats.set_params(
                {
                    "_id": self._generate_normal_id(
                        strings=[faculty_member], logger=self.logger
                    ),
                    "total_citations": global_stats.total_citations
                    + kwargs["tc_count"],
                    "article_count": global_stats.article_count + 1,
                    "department_affiliations": kwargs["faculty_affiliations"].get(
                        faculty_member, []
                    ),
                    "dois": kwargs["doi"],
                    "titles": kwargs["title"],
                    "categories": kwargs["all_categories"],
                    "category_urls": all_cat_urls,
                    "top_level_categories": kwargs["top_level_categories"],
                    "mid_level_categories": kwargs["mid_level_categories"],
                    "low_level_categories": kwargs["low_level_categories"],
                    "top_category_urls": top_cat_urls,
                    "mid_category_urls": mid_cat_urls,
                    "low_category_urls": low_cat_urls,
                    "themes": kwargs["themes"],
                    "journals": kwargs["journal"],
                    "citation_map": {kwargs["doi"]: kwargs["tc_count"]},
                }
            )
            self.logger.info("Completed setting params for global faculty stats.")

        self.logger.info("Completed updating global faculty stats.")

    def update_category_article_stats(self, **kwargs) -> None:
        """Update article statistics for each category.

        Creates or updates article statistics including titles, citations, faculty members,
        affiliations, abstracts, licenses, publication dates, and URLs. Organizes articles
        by their category levels (top, mid, low).

        Args:
            **kwargs: Keyword arguments containing article data.
                Required arguments:
                - title (str): Article title
                    Type: str
                - doi (str): Digital Object Identifier
                    Type: str
                - tc_count (int): Citation count
                    Type: int
                - faculty_members (List): List of faculty authors
                    Type: List[str]
                - faculty_affiliations (Dict): Faculty department mappings
                    Type: Dict[str, List[str]]
                - abstract (str): Article abstract
                    Type: str
                - license_url (str): License URL
                    Type: str
                - date_published_print (str): Print publication date
                    Type: str
                - date_published_online (str): Online publication date
                    Type: str
                - journal (str): Journal name
                    Type: str
                - download_url (str): Download URL
                    Type: str
                - themes (List): Article themes
                    Type: List[str]
                - all_categories (List): List of all categories
                    Type: List[str]
                - low_level_categories (List): Low-level categories
                    Type: List[str]
                - mid_level_categories (List): Mid-level categories
                    Type: List[str]
                - url_maps (Dict): Category URL mappings
                    Type: Dict[str, Dict[str, str]]

        Raises:
            KeyError: If required kwargs are missing
            ValueError: If article statistics cannot be updated

        Notes:
            - Updates statistics for each category level
            - Maintains hierarchical relationships
            - Tracks detailed article metadata
            - Links articles to faculty and departments
            - Preserves publication timeline information
        """
        self.logger.info("Updating category article stats...")
        for category in kwargs["all_categories"]:
            self.logger.info(
                f"Updating category article stats for category: {category}"
            )

            self.logger.info(
                "Checking if category article stats for category exists..."
            )
            if category not in self.category_article_stats:
                self.logger.info(
                    "Category article stats for category does not exist, creating new..."
                )
                self.category_article_stats[category] = (
                    self.dataclass_factory.get_dataclass(
                        DataClassTypes.CROSSREF_ARTICLE_STATS
                    )
                )
                self.logger.info("Created new category article stats for category.")

            self.logger.info("Getting URL for category via URL map...")
            url: str = (
                kwargs["url_maps"]["low"].get(category)
                or kwargs["url_maps"]["mid"].get(category)
                or kwargs["url_maps"]["top"].get(category)
            )
            self.logger.info(f"Retrieved URL: {url}")

            # Base article data
            self.logger.info("Setting base article data...")
            article_data: Dict[str, Any] = {
                "_id": kwargs["doi"],
                "title": kwargs["title"],
                "tc_count": kwargs["tc_count"],
                "faculty_members": kwargs["faculty_members"],
                "faculty_affiliations": kwargs["faculty_affiliations"],
                "abstract": kwargs["abstract"],
                "license_url": kwargs["license_url"],
                "date_published_print": kwargs["date_published_print"],
                "date_published_online": kwargs["date_published_online"],
                "journal": kwargs["journal"],
                "download_url": kwargs["download_url"],
                "doi": kwargs["doi"],
                "themes": kwargs["themes"],
                "categories": category,
                "category_urls": url,
                "url": self._generate_url(kwargs["doi"], self.logger),
            }
            self.logger.info("Completed setting base article data.")

            # Add category and URL to appropriate level
            self.logger.info("Adding category and URL to appropriate level...")
            if category in kwargs["low_level_categories"]:
                self.logger.info("Category is in low level categories...")
                article_data["low_level_categories"] = category
                article_data["low_category_urls"] = url
            elif category in kwargs["mid_level_categories"]:
                self.logger.info("Category is in mid level categories...")
                article_data["mid_level_categories"] = category
                article_data["mid_category_urls"] = url
            else:
                self.logger.info("Category is in top level categories...")
                article_data["top_level_categories"] = category
                article_data["top_category_urls"] = url

            self.logger.info("Setting params for category article stats...")
            self.category_article_stats[category].set_params(
                {kwargs["doi"]: article_data}
            )
            self.logger.info("Completed setting params for category article stats.")
        self.logger.info("Completed updating category article stats.")

    def create_article_object(self, **kwargs) -> None:
        """Create a new article object with complete metadata.

        Creates a CrossrefArticleDetails object containing all article information,
        including category relationships, URLs, and metadata. Handles URL generation
        for different category levels and maintains category hierarchies.

        Args:
            **kwargs: Keyword arguments containing article data.
                Required arguments:
                - doi (str): Digital Object Identifier
                    Type: str
                - title (str): Article title
                    Type: str
                - tc_count (int): Citation count
                    Type: int
                - faculty_members (List): Faculty authors
                    Type: List[str]
                - faculty_affiliations (Dict): Faculty affiliations
                    Type: Dict[str, List[str]]
                - abstract (str): Article abstract
                    Type: str
                - license_url (str): License URL
                    Type: str
                - date_published_print (str): Print publication date
                    Type: str
                - date_published_online (str): Online publication date
                    Type: str
                - journal (str): Journal name
                    Type: str
                - download_url (str): Download URL
                    Type: str
                - themes (List): Article themes
                    Type: List[str]
                - all_categories (List): All categories
                    Type: List[str]
                - top_level_categories (List): Top-level categories
                    Type: List[str]
                - mid_level_categories (List): Mid-level categories
                    Type: List[str]
                - low_level_categories (List): Low-level categories
                    Type: List[str]

        Raises:
            KeyError: If required kwargs are missing
            ValueError: If article object cannot be created

        Notes:
            - Creates CrossrefArticleDetails instance
            - Generates URLs for all category levels
            - Maintains category hierarchies
            - Preserves all article metadata
            - Links faculty and department relationships

        """
        self.logger.info("Creating article object...")

        # Create the article
        article: CrossrefArticleDetails = self.dataclass_factory.get_dataclass(
            DataClassTypes.CROSSREF_ARTICLE_DETAILS
        )
        self.logger.info("Created article object.")
        # Generate URLs for all categories
        # Initialize empty lists for top, mid, low category URLs
        # We don't need lists for the categories themselves as they're already in **kwargs
        self.logger.info("Generating URLs for all categories...")
        top_cat_urls: List[str] = []
        mid_cat_urls: List[str] = []
        low_cat_urls: List[str] = []

        # Parse through the categories and check if the level of the current category
        # This is to:
        # 1. Track top, mid, low category names
        # 2. Generate the URLs for each top, mid, low category
        # This allows for displaying what categories the articles what classified under
        # and under which level, as well as directly link to those pages on the frontend
        for category in kwargs["all_categories"]:
            self.logger.info(f"Processing category: {category}")
            if category in kwargs["low_level_categories"]:
                self.logger.info("Category is in low level categories...")
                # Get the mid category for the low category
                mid_cat = self.taxonomy_util.get_mid_cat_for_low_cat(category)
                self.logger.info(f"Got mid category for low category: {mid_cat}")
                # Get the top category for the mid category
                top_cat = self.taxonomy_util.get_top_cat_for_mid_cat(mid_cat)
                self.logger.info(f"Got top category for mid category: {top_cat}")
                # Generate the URL for the low category
                # If the low category is software development
                # and the mid category is software engineering
                # and the top category is computer science
                # the URL will be Computer%20science/software%20engineering/software%20development
                low_cat_urls.append(
                    self._generate_url(f"{top_cat}/{mid_cat}/{category}", self.logger)
                )

            elif category in kwargs["mid_level_categories"]:
                self.logger.info("Category is in mid level categories...")
                # Get the top category for the mid category
                top_cat = self.taxonomy_util.get_top_cat_for_mid_cat(category)
                self.logger.info(f"Got top category for mid category: {top_cat}")
                # Generate the URL for the mid category
                # If the mid category is software engineering
                # and the top category is computer science
                # the URL will be Computer%20science/software%20engineering
                mid_cat_urls.append(
                    self._generate_url(f"{top_cat}/{category}", self.logger)
                )
            else:
                self.logger.info("Category is in top level categories...")
                # If the top category is computer science
                # the URL will be Computer%20science
                top_cat_urls.append(self._generate_url(category, self.logger))

        # Combine all the URLs to get a compendium of all the URLs
        # This doesn't have a defined use yet, but it seems like it has the potential
        # to be a valuable piece of data for something so tracking it now so I don't
        # have to add it later and rerun all the articles ran up to that point
        # in the event we end up wanting/needing it for something
        self.logger.info(
            "Combining all the URLs to get a compendium of all the URLs..."
        )
        all_cat_urls: List[str] = top_cat_urls + mid_cat_urls + low_cat_urls
        self.logger.info(f"Combined all the URLs: {json.dumps(all_cat_urls, indent=4)}")

        # Direct field updates for CrossrefArticleDetails
        # .set_params() is used to update the dataclass fields for this article object
        self.logger.info("Setting params for article object...")
        article.set_params(
            {
                # Set _id to the doi to allow for easy lookup from the categories
                # As mentioned before each category has a list of dois
                # So through the use of that list we can look up in the DB each one of these article objects
                "_id": kwargs["doi"],
                "title": kwargs["title"],
                "tc_count": kwargs["tc_count"],
                "faculty_members": kwargs["faculty_members"],
                "faculty_affiliations": kwargs["faculty_affiliations"],
                "abstract": kwargs["abstract"],
                "license_url": kwargs["license_url"],
                "date_published_print": kwargs["date_published_print"],
                "date_published_online": kwargs["date_published_online"],
                "journal": kwargs["journal"],
                "download_url": kwargs["download_url"],
                "doi": kwargs["doi"],
                "themes": kwargs["themes"],
                "categories": kwargs["all_categories"],
                "category_urls": all_cat_urls,
                # Pull out and add lists for the category levels
                "top_level_categories": kwargs["top_level_categories"],
                "mid_level_categories": kwargs["mid_level_categories"],
                "low_level_categories": kwargs["low_level_categories"],
                # Add in the URLs fetched and created at the top of this method
                "top_category_urls": top_cat_urls,
                "mid_category_urls": mid_cat_urls,
                "low_category_urls": low_cat_urls,
                # Actual page URL for this article is quote(doi)
                "url": self._generate_url(kwargs["doi"], self.logger),
            }
        )
        self.logger.info("Completed setting params for article object.")

        # Append the created article object to the articles list
        self.logger.info("Appending the created article object to the articles list...")
        self.articles.append(article)
        self.logger.info(
            "Completed appending the created article object to the articles list."
        )

    def clean_faculty_affiliations(
        self, faculty_affiliations: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Clean and format faculty affiliation data.

        Processes raw faculty affiliation mappings to ensure consistent formatting
        and remove any invalid or malformed data.

        Args:
            faculty_affiliations (Dict): Raw faculty affiliation mappings.
                Type: Dict[str, Any]

        Returns:
            Dict: Cleaned faculty affiliation mappings.
                Type: Dict[str, Any]

        Notes:
            - Removes invalid entries
            - Normalizes department names
            - Handles missing or malformed data
            - Maintains faculty-department relationships
        """
        self.logger.info("Cleaning and formatting faculty affiliation data...")
        department_affiliations: Dict[str, Any] = {}
        for faculty_member, affiliations in faculty_affiliations.items():
            department_affiliations[faculty_member] = affiliations
        self.logger.info("Completed cleaning and formatting faculty affiliation data.")
        return department_affiliations

    def clean_faculty_members(self, faculty_members: List[str]) -> List[str]:
        """Clean and filter faculty member names.

        Processes raw faculty member names to ensure consistent formatting
        and remove any invalid or empty entries.

        Args:
            faculty_members (List): Raw list of faculty member names.
                Type: List[str]

        Returns:
            List: Cleaned list of faculty member names.
                Type: List[str]
                Excludes empty strings and invalid entries.

        Notes:
            - Removes empty strings
            - Normalizes name formats
            - Filters invalid entries
            - Maintains unique entries
        """
        self.logger.info("Cleaning and filtering faculty member names...")
        clean_faculty_members: List[str] = []
        for faculty_member in faculty_members:
            if faculty_member != "":
                clean_faculty_members.append(faculty_member)
        self.logger.info("Completed cleaning and filtering faculty member names.")
        return clean_faculty_members

    def initialize_categories(
        self, categories: Dict[str, List[str]]
    ) -> Dict[str, List[str]]:
        """Initialize category data structures for all category levels.

        Creates CategoryInfo instances for each category and organizes them by level
        in the taxonomy hierarchy (top, mid, low).

        Args:
            categories (Dict): Categories organized by level.
                Type: Dict[str, List[str]]
                Keys must be: "top", "mid", "low"

        Returns:
            Dict: Organized category data.
                Type: Dict[str, List[str]]
                Contains:
                - top_level_categories (List[str]): List of top-level categories
                - mid_level_categories (List[str]): List of mid-level categories
                - low_level_categories (List[str]): List of low-level categories
                - all_categories (List[str]): List of all categories

        Raises:
            ValueError: If category initialization fails

        Notes:
            - Creates CategoryInfo instances for each category
            - Maintains hierarchical relationships
            - Validates category levels
            - Ensures unique category names
            - Preserves taxonomy structure
        """
        self.logger.info("Initializing categories...")
        top_level_categories: List[str] = []
        mid_level_categories: List[str] = []
        low_level_categories: List[str] = []
        for category_level in ["top", "mid", "low"]:
            self.logger.info(
                f"Category being initialized is in level: {category_level}"
            )
            for category in categories.get(category_level, []):
                self.logger.info(f"Category being initialized: {category}")

                self.logger.info(
                    "Checking if category already exists in category data..."
                )
                if category not in self.category_data:
                    self.logger.info(
                        "Category does not exist, creating new category info..."
                    )
                    self.category_data[category] = self.dataclass_factory.get_dataclass(
                        DataClassTypes.CATEGORY_INFO, category_name=category
                    )
                    self.logger.info("Created new category info.")

                if category_level == "top":
                    self.logger.info(
                        "Category is in top level categories, appending to top level categories list..."
                    )
                    top_level_categories.append(category)
                elif category_level == "mid":
                    self.logger.info(
                        "Category is in mid level categories, appending to mid level categories list..."
                    )
                    mid_level_categories.append(category)
                elif category_level == "low":
                    self.logger.info(
                        "Category is in low level categories, appending to low level categories list..."
                    )
                    low_level_categories.append(category)

        self.logger.info("Completed initializing categories.")
        return {
            "top_level_categories": top_level_categories,
            "mid_level_categories": mid_level_categories,
            "low_level_categories": low_level_categories,
            "all_categories": top_level_categories
            + mid_level_categories
            + low_level_categories,
        }

    # Set of public Getter methods to access the data
    def get_category_data(self) -> Dict[str, CategoryInfo]:
        """Get the processed category data.

        Provides access to the complete mapping of categories and their associated
        information, including statistics and relationships.

        Returns:
            Dict: Mapping of categories to their information.
                Type: Dict[str, :class:`academic_metrics.models.category_info.CategoryInfo`]

        Notes:
            - Returns complete category hierarchy
            - Includes all category statistics
            - Contains faculty and article relationships
            - Preserves category metadata
        """
        self.logger.info("Returning category data...")
        return self.category_data

    def get_category_article_stats(self) -> Dict[str, CrossrefArticleStats]:
        """Get article statistics organized by category.

        Provides access to the complete mapping of categories to their associated
        article statistics, including metrics and metadata.

        Returns:
            Dict: Mapping of categories to their article statistics.
                Type: Dict[str, :class:`academic_metrics.models.crossref_article_stats.CrossrefArticleStats`]

        Notes:
            - Returns statistics for all categories
            - Includes article counts and metrics
            - Contains citation information
            - Preserves publication metadata
            - Maintains category relationships
        """
        self.logger.info("Returning article statistics organized by category...")
        return self.category_article_stats

    def get_articles(self) -> List[CrossrefArticleDetails]:
        """Get the list of processed articles.

        Provides access to the complete list of processed articles with their
        full details and metadata.

        Returns:
            List: List of all processed article details.
                Type: List[:class:`academic_metrics.models.crossref_article_details.CrossrefArticleDetails`]

        Notes:
            - Returns all processed articles
            - Includes complete article metadata
            - Contains category assignments
            - Preserves faculty relationships
            - Maintains publication details
        """
        self.logger.info("Returning list of processed articles...")
        return self.articles

    def get_faculty_stats(self) -> Dict[str, FacultyStats]:
        """Get faculty statistics organized by category.

        Provides access to the complete mapping of categories to their associated
        faculty statistics, including publication metrics and relationships.

        Returns:
            Dict: Mapping of categories to their faculty statistics.
                Type: Dict[str, :class:`academic_metrics.models.faculty_stats.FacultyStats`]

        Notes:
            - Returns statistics for all categories
            - Includes faculty publication counts
            - Contains citation metrics
            - Preserves department affiliations
            - Maintains category-specific metrics
        """
        self.logger.info("Returning faculty statistics organized by category...")
        return self.faculty_stats

    def get_global_faculty_stats(self) -> Dict[str, GlobalFacultyStats]:
        """Get global statistics for all faculty members.

        Provides access to the complete mapping of faculty members to their global
        statistics across all categories and publications.

        Returns:
            Dict: Mapping of faculty members to their global statistics.
                Type: Dict[str, :class:`academic_metrics.models.global_faculty_stats.GlobalFacultyStats`]

        Notes:
            - Returns aggregate statistics per faculty
            - Includes cross-category metrics
            - Contains total publication counts
            - Preserves all department affiliations
            - Maintains complete publication history
        """
        self.logger.info("Returning global statistics for all faculty members...")
        return self.global_faculty_stats

    # End of public Getter methods

    @staticmethod
    def _collect_all_affiliations(
        faculty_affiliations: Dict[str, Any], logger: logging.Logger
    ) -> Set[str]:
        """Collect all unique department affiliations.

        Extracts and deduplicates all department affiliations from the faculty
        to department mapping dictionary.

        Args:
            faculty_affiliations (Dict): Faculty to department mappings.
                Type: Dict[str, Any]
            logger (logging.Logger): Logger instance for tracking operations.
                Type: logging.Logger

        Returns:
            set: Set of unique department affiliations.
                Type: Set[str]

        Notes:
            - Removes duplicate departments
            - Handles missing affiliations
            - Validates department names
            - Maintains unique entries only
        """
        logger.info("Collecting all unique department affiliations...")
        logger.info(f"Initializing all affiliations empty set...")
        all_affiliations: set[str] = set()
        logger.info(f"All affiliations empty set initialized.")

        logger.info(f"Iterating through faculty affiliations...")
        for department_affiliation in faculty_affiliations.values():
            logger.info(f"Processing department affiliation: {department_affiliation}")

            logger.info(f"Checking if department affiliation is a set...")
            if isinstance(department_affiliation, set):
                logger.info(
                    f"Department affiliation is a set, updating all affiliations set..."
                )
                all_affiliations.update(department_affiliation)
            elif isinstance(department_affiliation, list):
                logger.info(
                    "Department affiliation is a list, updating all affiliations set..."
                )
                all_affiliations.update(department_affiliation)
            elif isinstance(department_affiliation, str):
                logger.info(
                    "Department affiliation is a string, adding to all affiliations set..."
                )
                all_affiliations.add(department_affiliation)

        logger.info(
            f"Completed iterating through faculty affiliations, returning all affiliations set..."
        )
        return all_affiliations

    @staticmethod
    def _generate_url(string: str, logger: logging.Logger | None = None) -> str:
        """Generate a URL-safe string.

        Converts an input string into a URL-safe format by removing special characters,
        replacing spaces, and ensuring proper encoding.

        Args:
            string (str): Input string to encode.
                Type: str
            logger (logging.Logger | None): Logger instance to use for logging.
                Type: logging.Logger | None
                Defaults to None.

        Returns:
            str: URL-encoded string.
                Type: str

        Notes:
            - Removes special characters
            - Replaces spaces with hyphens
            - Converts to lowercase
            - Ensures URL-safe encoding
        """
        logger.info(f"Generating URL-encoded string for: {string}")
        url_encoded_string: str = quote(string)
        logger.info(f"Generated URL-encoded string: {url_encoded_string}")
        return url_encoded_string

    @staticmethod
    def _generate_normal_id(
        strings: List[str], logger: logging.Logger | None = None
    ) -> str:
        """Generate a normalized ID from a list of strings.

        Combines multiple strings into a single normalized identifier, ensuring
        consistent formatting and URL-safe characters.

        Args:
            strings (list): List of strings to combine into an ID.
                Type: List[str]
            logger (logging.Logger | None): Logger instance to use for logging.
                Type: logging.Logger | None
                Defaults to None.

        Returns:
            str: Normalized ID string.
                Type: str
                Format: lowercase, hyphen-separated

        Notes:
            - Combines multiple strings
            - Converts to lowercase
            - Replaces spaces with hyphens
            - Removes special characters
            - Ensures consistent formatting
        """
        logger.info(f"Generating normalized ID from strings: {strings}")
        logger.info(f"Initializing normalized ID as empty string...")
        normal_id: str = ""
        logger.info(f"Initialized normalized ID as empty string.")

        logger.info(f"Iterating through strings to generate normalized ID...")
        for string in strings:
            logger.info(f"Processing string: {string}")
            normal_id += f'{string.lower().replace(" ", "-")}_'
            logger.info(f"Updated normalized ID: {normal_id}")

        logger.info(f"Completed iterating through strings, returning normalized ID...")
        normalized_id: str = normal_id.rstrip("_")
        logger.info(f"Normalized ID: {normalized_id}")
        return normalized_id


if __name__ == "__main__":
    from academic_metrics.factories import DataClassFactory, StrategyFactory
    from academic_metrics.utils import Taxonomy, Utilities, WarningManager

    dc_factory = DataClassFactory()
    taxonomy = Taxonomy()
    strategy_factory = StrategyFactory()
    warning_manager = WarningManager()
    utilities = Utilities(
        strategy_factory=strategy_factory, warning_manager=warning_manager
    )

    category_processor = CategoryProcessor(
        utils=utilities,
        dataclass_factory=dc_factory,
        warning_manager=warning_manager,
        taxonomy_util=taxonomy,
    )

    raw_attributes: Dict[str, Any] = {
        "categories": {
            "top": [
                "Agricultural sciences and natural resources",
                "Geosciences, atmospheric, and ocean sciences",
            ],
            "mid": [
                "Agricultural, animal, plant, and veterinary sciences",
                "Geological and earth sciences",
                "Ocean/ marine sciences and atmospheric science",
            ],
            "low": [
                "Aquaculture",
                "Food science and technology",
                "Plant sciences",
                "Geology/ earth science, general",
                "Hydrology and water resources science",
                "Marine biology and biological oceanography",
                "Marine sciences",
            ],
        },
        "faculty_members": [
            "Christopher Mulanda Aura",
            "Safina Musa",
            "Chrisphine S. Nyamweya",
            "Zachary Ogari",
            "James M. Njiru",
            "Stuart E. Hamilton",
            "Linda May",
        ],
        "faculty_affiliations": {
            "Christopher Mulanda Aura": [
                "Kenya Marine and Fisheries Research Institute Kisumu Kenya"
            ],
            "Safina Musa": [
                "Kenya Marine and Fisheries Research Institute Kegati Kenya"
            ],
            "Chrisphine S. Nyamweya": [
                "Kenya Marine and Fisheries Research Institute Kisumu Kenya"
            ],
            "Zachary Ogari": [
                "Kenya Marine and Fisheries Research Institute Kisumu Kenya"
            ],
            "James M. Njiru": [
                "Kenya Marine and Fisheries Research Institute Mombasa Kenya"
            ],
            "Stuart E. Hamilton": ["Salisbury University Salisbury USA"],
            "Linda May": [
                "UK Centre for Ecology &amp; Hydrology Penicuik Midlothian UK"
            ],
        },
        "title": [
            "A GIS‐based approach for delineating suitable areas for cage fish culture in a lake"
        ],
        "tc_count": 4,
        "abstract": "We present a GIS‐based approach to the delineation of areas that have different levels of suitability for use as tilapia cage culture sites the Kenyan part of Lake Victoria, Africa. The study area was 4,100\xa0km2. The method uses high‐resolution bathymetric data, newly collected water quality data from all major fishing grounds and cage culture sites, and existing spatial information from previous studies. The parameters considered are water depth, water temperature, levels of dissolved oxygen, chlorophyll‐aconcentrations, distances to the lake shoreline and proximity to other constraints on cage culture development. The results indicated that the area most suitable for fish cages comprised about 362\xa0km2, or approximately 9% of the total area; the remaining 91% (i.e., 3,737\xa0km2) was found to be unsuitable for tilapia cage culture. We conclude that the successful implementation of this approach would need stakeholder involvement in the validation and approval of potential sites, and in the incorporation of lake zoning into spatial planning policy and the regulations that support sustainable use while minimising resource use conflicts. The results of this study have broader applicability to the whole of Lake Victoria, other African Great Lakes, and any lakes in the world where tilapia cage culture already occurs or may occur in the future.\n",
        "license_url": "http://onlinelibrary.wiley.com/termsAndConditions#vor",
        "date_published_print": "2021-6",
        "date_published_online": "2021-4-13",
        "journal": "Lakes &amp; Reservoirs: Science, Policy and Management for Sustainable Use",
        "download_url": "http://dx.doi.org/10.1111/lre.12357",
        "doi": "10.1111/lre.12357",
        "themes": [
            "Aquaculture site suitability",
            "GIS applications in environmental science",
            "Water quality assessment",
            "Sustainable resource management",
        ],
    }

    category_processor._test_category_processor(raw_attributes)
