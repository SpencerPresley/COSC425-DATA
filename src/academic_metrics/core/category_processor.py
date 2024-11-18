from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any, Dict, List, Set, Tuple
from urllib.parse import quote

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

from academic_metrics.constants import LOG_DIR_PATH
from academic_metrics.enums import AttributeTypes, DataClassTypes


class CategoryProcessor:
    """Processes and organizes academic publication data by categories.

    This class handles the processing of classified publication data, organizing it into
    categories and generating various statistics. It manages faculty affiliations,
    article details, and category relationships.

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

    Public Methods:
        process_data_list: Process a list of publication data items.
        get_category_data: Get processed category data.
        get_category_article_stats: Get article statistics by category.
        get_articles: Get list of processed articles.
        get_faculty_stats: Get faculty statistics by category.
        get_global_faculty_stats: Get global faculty statistics.

    Private Methods:
        call_get_attributes: Extract attributes from raw data.
        update_category_stats: Update statistics for a category.
        update_faculty_stats: Update faculty statistics.
        update_global_faculty_stats: Update global faculty statistics.
        update_category_article_stats: Update article statistics by category.
        create_article_object: Create a new article object.
        clean_faculty_affiliations: Clean faculty affiliation data.
        clean_faculty_members: Clean faculty member data.
        initialize_categories: Initialize category data structures.
        _collect_all_affiliations: Collect all faculty affiliations.
        _generate_url: Generate URL from string.
        _generate_normal_id: Generate normalized ID from strings.
    """

    def __init__(
        self,
        utils: Utilities,
        dataclass_factory: DataClassFactory,
        warning_manager: WarningManager,
        taxonomy_util: Taxonomy,
        log_to_console: bool = True,
    ) -> None:
        """Initialize the CategoryProcessor with required dependencies.

        Sets up logging configuration and initializes all required components for
        processing publication data, including utilities, factories, and data structures
        for storing category, faculty, and article information.

        Args:
            utils (Utilities): Utility functions for data processing.
            dataclass_factory (DataClassFactory): Factory for creating data model instances.
            warning_manager (WarningManager): System for handling and logging warnings.
            taxonomy_util (Taxonomy): Utility for managing publication taxonomy.
            log_to_console (bool, optional): Whether to log output to console. Defaults to True.

        Raises:
            ValueError: If required dependencies are not properly initialized.
            IOError: If log file cannot be created or accessed.
        """
        # Set up logger
        self.log_file_path: str = os.path.join(LOG_DIR_PATH, "category_processor.log")
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.logger.handlers = []
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler: logging.FileHandler = logging.FileHandler(self.log_file_path)
            formatter: logging.Formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            console_handler: logging.StreamHandler | None = (
                logging.StreamHandler() if log_to_console else None
            )
            if console_handler:
                console_handler.setFormatter(formatter)
                self.logger.addHandler(console_handler)

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

        Raises:
            ValueError: If required attributes are missing from data.
            Exception: If category information cannot be initialized.
        """
        for item in data:
            # Get base attributes
            raw_attributes = self.call_get_attributes(data=item)
            print(f"\n\nRAW ATTRIBUTES:\n{raw_attributes}\n\n")

            # Get category information
            category_levels: Dict[str, List[str]] = self.initialize_categories(
                raw_attributes.get("categories", [])
            )

            # Fetch out seperate category levels
            top_categories: List[str] = category_levels.get("top_level_categories", [])
            mid_categories: List[str] = category_levels.get("mid_level_categories", [])
            low_categories: List[str] = category_levels.get("low_level_categories", [])
            all_categories: List[str] = category_levels.get("all_categories", [])

            # Create URL maps for each category level
            top_level_url_map: Dict[str, str] = {}
            mid_level_url_map: Dict[str, str] = {}
            low_level_url_map: Dict[str, str] = {}

            for category in all_categories:
                if category in low_categories:
                    mid_cat = self.taxonomy_util.get_mid_cat_for_low_cat(category)
                    top_cat = self.taxonomy_util.get_top_cat_for_mid_cat(mid_cat)
                    low_level_url_map[category] = self._generate_url(
                        f"{top_cat}/{mid_cat}/{category}"
                    )
                elif category in mid_categories:
                    top_cat = self.taxonomy_util.get_top_cat_for_mid_cat(category)
                    mid_level_url_map[category] = self._generate_url(
                        f"{top_cat}/{category}"
                    )
                else:
                    top_level_url_map[category] = self._generate_url(category)

            # Clean special fields
            faculty_members = self.clean_faculty_members(
                raw_attributes.get("faculty_members", [])
            )
            faculty_affiliations = self.clean_faculty_affiliations(
                raw_attributes.get("faculty_affiliations", [])
            )
            all_affiliations = self._collect_all_affiliations(faculty_affiliations)

            # Unpack everything into kwargs
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

            self.update_category_stats(**kwargs)
            self.update_faculty_stats(**kwargs)
            self.update_global_faculty_stats(**kwargs)
            self.update_category_article_stats(**kwargs)
            self.create_article_object(**kwargs)

    def call_get_attributes(self, *, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and process attributes from raw publication data.

        Extracts various attributes including categories, authors, departments, titles,
        citations, abstracts, licenses, publication dates, journal info, URLs, DOIs,
        and themes from the raw data.

        Args:
            data (Dict[str, Any]): Raw publication data dictionary.

        Returns:
            Dict[str, Any]: Dictionary containing extracted and processed attributes:
                - categories: List of publication categories
                - faculty_members: List of faculty authors
                - faculty_affiliations: Dictionary mapping faculty to their departments
                - title: Publication title
                - tc_count: Citation count
                - abstract: Publication abstract
                - license_url: License URL
                - date_published_print: Print publication date
                - date_published_online: Online publication date
                - journal: Journal name
                - download_url: Download URL
                - doi: Digital Object Identifier
                - themes: List of publication themes

        Raises:
            Exception: If no category is found in the data.
        """
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

        if attribute_results[AttributeTypes.CROSSREF_CATEGORIES][0]:
            categories: List[str] = attribute_results[
                AttributeTypes.CROSSREF_CATEGORIES
            ][1]
        else:
            raise Exception(f"No category found for data: {data}")

        faculty_members: List[str] | None = (
            attribute_results[AttributeTypes.CROSSREF_AUTHORS][1]
            if attribute_results[AttributeTypes.CROSSREF_AUTHORS][0]
            else None
        )
        faculty_affiliations: Dict[str, List[str]] | None = (
            attribute_results[AttributeTypes.CROSSREF_DEPARTMENTS][1]
            if attribute_results[AttributeTypes.CROSSREF_DEPARTMENTS][0]
            else None
        )
        title: str | None = (
            attribute_results[AttributeTypes.CROSSREF_TITLE][1]
            if attribute_results[AttributeTypes.CROSSREF_TITLE][0]
            else None
        )
        tc_count: int | None = (
            attribute_results[AttributeTypes.CROSSREF_CITATION_COUNT][1]
            if attribute_results[AttributeTypes.CROSSREF_CITATION_COUNT][0]
            else None
        )
        abstract: str | None = (
            attribute_results[AttributeTypes.CROSSREF_ABSTRACT][1]
            if attribute_results[AttributeTypes.CROSSREF_ABSTRACT][0]
            else None
        )
        license_url: str | None = (
            attribute_results[AttributeTypes.CROSSREF_LICENSE_URL][1]
            if attribute_results[AttributeTypes.CROSSREF_LICENSE_URL][0]
            else None
        )
        date_published_print: str | None = (
            attribute_results[AttributeTypes.CROSSREF_PUBLISHED_PRINT][1]
            if attribute_results[AttributeTypes.CROSSREF_PUBLISHED_PRINT][0]
            else None
        )
        date_published_online: str | None = (
            attribute_results[AttributeTypes.CROSSREF_PUBLISHED_ONLINE][1]
            if attribute_results[AttributeTypes.CROSSREF_PUBLISHED_ONLINE][0]
            else None
        )
        journal: str | None = (
            attribute_results[AttributeTypes.CROSSREF_JOURNAL][1]
            if attribute_results[AttributeTypes.CROSSREF_JOURNAL][0]
            else None
        )
        download_url: str | None = (
            attribute_results[AttributeTypes.CROSSREF_URL][1]
            if attribute_results[AttributeTypes.CROSSREF_URL][0]
            else None
        )
        doi: str | None = (
            attribute_results[AttributeTypes.CROSSREF_DOI][1]
            if attribute_results[AttributeTypes.CROSSREF_DOI][0]
            else None
        )
        themes: List[str] | None = (
            attribute_results[AttributeTypes.CROSSREF_THEMES][1]
            if attribute_results[AttributeTypes.CROSSREF_THEMES][0]
            else None
        )
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
            **kwargs: Keyword arguments containing article data:
                title (str): Article title
                doi (str): Digital Object Identifier
                tc_count (int): Citation count
                faculty_members (List[str]): List of faculty authors
                all_affiliations (Set[str]): Set of department affiliations
                themes (List[str]): List of article themes
                all_categories (List[str]): List of all categories
                url_maps (Dict[str, Dict[str, str]]): Category URL mappings

        Raises:
            KeyError: If required kwargs are missing.
            ValueError: If category information cannot be updated.
        """
        for category in kwargs["all_categories"]:
            url: str = (
                kwargs["url_maps"]["low"].get(category, "")
                or kwargs["url_maps"]["mid"].get(category, "")
                or kwargs["url_maps"]["top"].get(category, "")
            )
            category_info: CategoryInfo = self.category_data[category]
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

            # Update counts based on set lengths after deduplication by the set_params() method
            category_info.faculty_count = len(category_info.faculty)
            category_info.department_count = len(category_info.departments)
            category_info.article_count = len(category_info.titles)
            category_info.citation_average = (
                category_info.tc_count / category_info.article_count
            )

    def update_faculty_stats(self, **kwargs) -> None:
        """Update faculty statistics for each category.

        Updates faculty member information including department affiliations,
        publication titles, DOIs, citation counts, and article counts. Creates
        or updates faculty statistics entries for each category.

        Args:
            **kwargs: Keyword arguments containing faculty and article data:
                faculty_members (List[str]): List of faculty authors
                faculty_affiliations (Dict[str, List[str]]): Faculty department mappings
                title (str): Article title
                doi (str): Digital Object Identifier
                tc_count (int): Citation count
                all_categories (List[str]): List of all categories
                url_maps (Dict[str, Dict[str, str]]): Category URL mappings

        Raises:
            KeyError: If required kwargs are missing.
            ValueError: If faculty statistics cannot be updated.
        """
        for category in kwargs["all_categories"]:
            if category not in self.faculty_stats:
                self.faculty_stats[category] = self.dataclass_factory.get_dataclass(
                    DataClassTypes.FACULTY_STATS,
                )

            url: str = (
                kwargs["url_maps"]["low"].get(category, "")
                or kwargs["url_maps"]["mid"].get(category, "")
                or kwargs["url_maps"]["top"].get(category, "")
            )

            for faculty_member in kwargs["faculty_members"]:
                faculty_data: Dict[str, Any] = {
                    "_id": self._generate_normal_id(strings=[faculty_member, category]),
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

                self.faculty_stats[category].set_params({faculty_member: faculty_data})

    def update_global_faculty_stats(self, **kwargs) -> None:
        """Update global statistics for each faculty member.

        Creates or updates global faculty statistics including total citations,
        article counts, department affiliations, DOIs, titles, categories,
        and category URLs across all publication categories.

        Args:
            **kwargs: Keyword arguments containing faculty and article data:
                faculty_members (List[str]): List of faculty authors
                faculty_affiliations (Dict[str, List[str]]): Faculty department mappings
                title (str): Article title
                doi (str): Digital Object Identifier
                tc_count (int): Citation count
                all_categories (List[str]): List of all categories
                top_level_categories (List[str]): Top-level categories
                mid_level_categories (List[str]): Mid-level categories
                low_level_categories (List[str]): Low-level categories
                url_maps (Dict[str, Dict[str, str]]): Category URL mappings
                themes (List[str]): Article themes
                journal (str): Journal name

        Raises:
            KeyError: If required kwargs are missing.
            ValueError: If global faculty statistics cannot be updated.
        """
        for faculty_member in kwargs["faculty_members"]:
            if faculty_member not in self.global_faculty_stats:
                self.global_faculty_stats[faculty_member] = (
                    self.dataclass_factory.get_dataclass(
                        DataClassTypes.GLOBAL_FACULTY_STATS, name=faculty_member
                    )
                )

            # Get all URLs from maps
            # This logic even confused me so here's a not of why they get everything
            # This is global faculty stats, so the goal is after processing all papers
            # We can see the faculty members stats across papers without having to sum up all the individual records provided by the standard faculty stats which only look an individual category stat totals

            top_cat_urls: List[str] = [
                kwargs["url_maps"]["top"].get(cat)
                for cat in kwargs["top_level_categories"]
                if kwargs["url_maps"]["top"].get(cat)
            ]
            mid_cat_urls: List[str] = [
                kwargs["url_maps"]["mid"].get(cat)
                for cat in kwargs["mid_level_categories"]
                if kwargs["url_maps"]["mid"].get(cat)
            ]
            low_cat_urls: List[str] = [
                kwargs["url_maps"]["low"].get(cat)
                for cat in kwargs["low_level_categories"]
                if kwargs["url_maps"]["low"].get(cat)
            ]
            all_cat_urls: List[str] = top_cat_urls + mid_cat_urls + low_cat_urls

            global_stats: GlobalFacultyStats = self.global_faculty_stats[faculty_member]
            global_stats.set_params(
                {
                    "_id": self._generate_normal_id(strings=[faculty_member]),
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

    def update_category_article_stats(self, **kwargs) -> None:
        """Update article statistics for each category.

        Creates or updates article statistics including titles, citations, faculty members,
        affiliations, abstracts, licenses, publication dates, and URLs. Organizes articles
        by their category levels (top, mid, low).

        Args:
            **kwargs: Keyword arguments containing article data:
                title (str): Article title
                doi (str): Digital Object Identifier
                tc_count (int): Citation count
                faculty_members (List[str]): List of faculty authors
                faculty_affiliations (Dict[str, List[str]]): Faculty department mappings
                abstract (str): Article abstract
                license_url (str): License URL
                date_published_print (str): Print publication date
                date_published_online (str): Online publication date
                journal (str): Journal name
                download_url (str): Download URL
                themes (List[str]): Article themes
                all_categories (List[str]): List of all categories
                low_level_categories (List[str]): Low-level categories
                mid_level_categories (List[str]): Mid-level categories
                url_maps (Dict[str, Dict[str, str]]): Category URL mappings

        Raises:
            KeyError: If required kwargs are missing.
            ValueError: If article statistics cannot be updated.
        """
        for category in kwargs["all_categories"]:
            if category not in self.category_article_stats:
                self.category_article_stats[category] = (
                    self.dataclass_factory.get_dataclass(
                        DataClassTypes.CROSSREF_ARTICLE_STATS
                    )
                )

            url: str = (
                kwargs["url_maps"]["low"].get(category)
                or kwargs["url_maps"]["mid"].get(category)
                or kwargs["url_maps"]["top"].get(category)
            )

            # Base article data
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
                "url": self._generate_url(kwargs["doi"]),
            }

            # Add category and URL to appropriate level
            if category in kwargs["low_level_categories"]:
                article_data["low_level_categories"] = category
                article_data["low_category_urls"] = url
            elif category in kwargs["mid_level_categories"]:
                article_data["mid_level_categories"] = category
                article_data["mid_category_urls"] = url
            else:
                article_data["top_level_categories"] = category
                article_data["top_category_urls"] = url

            self.category_article_stats[category].set_params(
                {kwargs["doi"]: article_data}
            )

    def create_article_object(self, **kwargs) -> None:
        """Create a new article object with complete metadata.

        Creates a CrossrefArticleDetails object containing all article information,
        including category relationships, URLs, and metadata. Handles URL generation
        for different category levels and maintains category hierarchies.

        Args:
            **kwargs: Keyword arguments containing article data:
                doi (str): Digital Object Identifier
                title (str): Article title
                tc_count (int): Citation count
                faculty_members (List[str]): Faculty authors
                faculty_affiliations (Dict[str, List[str]]): Faculty affiliations
                abstract (str): Article abstract
                license_url (str): License URL
                date_published_print (str): Print publication date
                date_published_online (str): Online publication date
                journal (str): Journal name
                download_url (str): Download URL
                themes (List[str]): Article themes
                all_categories (List[str]): All categories
                top_level_categories (List[str]): Top-level categories
                mid_level_categories (List[str]): Mid-level categories
                low_level_categories (List[str]): Low-level categories

        Raises:
            KeyError: If required kwargs are missing.
            ValueError: If article object cannot be created.
        """
        # Create the article
        article: CrossrefArticleDetails = self.dataclass_factory.get_dataclass(
            DataClassTypes.CROSSREF_ARTICLE_DETAILS
        )

        # Generate URLs for all categories
        # Initialize empty lists for top, mid, low category URLs
        # We don't need lists for the categories themselves as they're already in **kwargs
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
            if category in kwargs["low_level_categories"]:
                # Get the mid category for the low category
                mid_cat = self.taxonomy_util.get_mid_cat_for_low_cat(category)
                # Get the top category for the mid category
                top_cat = self.taxonomy_util.get_top_cat_for_mid_cat(mid_cat)
                # Generate the URL for the low category
                # If the low category is software development
                # and the mid category is software engineering
                # and the top category is computer science
                # the URL will be Computer%20science/software%20engineering/software%20development
                low_cat_urls.append(
                    self._generate_url(f"{top_cat}/{mid_cat}/{category}")
                )
            elif category in kwargs["mid_level_categories"]:
                # Get the top category for the mid category
                top_cat = self.taxonomy_util.get_top_cat_for_mid_cat(category)
                # Generate the URL for the mid category
                # If the mid category is software engineering
                # and the top category is computer science
                # the URL will be Computer%20science/software%20engineering
                mid_cat_urls.append(self._generate_url(f"{top_cat}/{category}"))
            else:
                # Generate the URL for the top category
                # If the top category is computer science
                # the URL will be Computer%20science
                top_cat_urls.append(self._generate_url(category))

        # Combine all the URLs to get a compendium of all the URLs
        # This doesn't have a defined use yet, but it seems like it has the potential
        # to be a valuable piece of data for something so tracking it now so I don't
        # have to add it later and rerun all the articles ran up to that point
        # in the event we end up wanting/needing it for something
        all_cat_urls: List[str] = top_cat_urls + mid_cat_urls + low_cat_urls

        # Direct field updates for CrossrefArticleDetails
        # .set_params() is used to update the dataclass fields for this article object
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
                "url": self._generate_url(kwargs["doi"]),
            }
        )

        # Append the created article object to the articles list
        self.articles.append(article)

    def clean_faculty_affiliations(
        self, faculty_affiliations: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Clean and format faculty affiliation data.

        Args:
            faculty_affiliations (Dict[str, Any]): Raw faculty affiliation mappings.

        Returns:
            Dict[str, Any]: Cleaned faculty affiliation mappings.
        """
        department_affiliations: Dict[str, Any] = {}
        for faculty_member, affiliations in faculty_affiliations.items():
            department_affiliations[faculty_member] = affiliations
        return department_affiliations

    def clean_faculty_members(self, faculty_members: List[str]) -> List[str]:
        """Clean and filter faculty member names.

        Args:
            faculty_members (List[str]): Raw list of faculty member names.

        Returns:
            List[str]: Cleaned list of faculty member names, excluding empty strings.
        """
        clean_faculty_members: List[str] = []
        for faculty_member in faculty_members:
            if faculty_member != "":
                clean_faculty_members.append(faculty_member)
        return clean_faculty_members

    def initialize_categories(
        self, categories: Dict[str, List[str]]
    ) -> Dict[str, List[str]]:
        """Initialize category data structures for all category levels.

        Creates CategoryInfo instances for each category and organizes them by level.

        Args:
            categories (Dict[str, List[str]]): Categories organized by level (top, mid, low).

        Returns:
            Dict[str, List[str]]: Organized category data including:
                - top_level_categories: List of top-level categories
                - mid_level_categories: List of mid-level categories
                - low_level_categories: List of low-level categories
                - all_categories: List of all categories

        Raises:
            ValueError: If category initialization fails.
        """
        top_level_categories: List[str] = []
        mid_level_categories: List[str] = []
        low_level_categories: List[str] = []
        for category_level in ["top", "mid", "low"]:
            for category in categories.get(category_level, []):
                if category not in self.category_data:
                    self.category_data[category] = self.dataclass_factory.get_dataclass(
                        DataClassTypes.CATEGORY_INFO, category_name=category
                    )
                if category_level == "top":
                    top_level_categories.append(category)
                elif category_level == "mid":
                    mid_level_categories.append(category)
                elif category_level == "low":
                    low_level_categories.append(category)
        return {
            "top_level_categories": top_level_categories,
            "mid_level_categories": mid_level_categories,
            "low_level_categories": low_level_categories,
            "all_categories": list(self.category_data.keys()),
        }

    # Set of public Getter methods to access the data
    def get_category_data(self) -> Dict[str, CategoryInfo]:
        """Get the processed category data.

        Returns:
            Dict[str, CategoryInfo]: Mapping of categories to their information.
        """
        return self.category_data

    def get_category_article_stats(self) -> Dict[str, CrossrefArticleStats]:
        """Get article statistics organized by category.

        Returns:
            Dict[str, CrossrefArticleStats]: Mapping of categories to their article statistics.
        """
        return self.category_article_stats

    def get_articles(self) -> List[CrossrefArticleDetails]:
        """Get the list of processed articles.

        Returns:
            List[CrossrefArticleDetails]: List of all processed article details.
        """
        return self.articles

    def get_faculty_stats(self) -> Dict[str, FacultyStats]:
        """Get faculty statistics organized by category.

        Returns:
            Dict[str, FacultyStats]: Mapping of categories to their faculty statistics.
        """
        return self.faculty_stats

    def get_global_faculty_stats(self) -> Dict[str, GlobalFacultyStats]:
        """Get global statistics for all faculty members.

        Returns:
            Dict[str, GlobalFacultyStats]: Mapping of faculty members to their global statistics.
        """
        return self.global_faculty_stats

    # End of public Getter methods

    @staticmethod
    def _collect_all_affiliations(faculty_affiliations: Dict[str, Any]) -> Set[str]:
        """Collect all unique department affiliations.

        Args:
            faculty_affiliations (Dict[str, Any]): Faculty to department mappings.

        Returns:
            Set[str]: Set of unique department affiliations.
        """
        all_affiliations: set[str] = set()
        for department_affiliation in faculty_affiliations.values():
            if isinstance(department_affiliation, set):
                all_affiliations.update(department_affiliation)
            elif isinstance(department_affiliation, list):
                all_affiliations.update(department_affiliation)
            elif isinstance(department_affiliation, str):
                all_affiliations.add(department_affiliation)
        return all_affiliations

    @staticmethod
    def _generate_url(string: str) -> str:
        """Generate a URL-safe string.

        Args:
            string (str): Input string to encode.

        Returns:
            str: URL-encoded string.
        """
        return quote(string)

    @staticmethod
    def _generate_normal_id(strings: List[str]) -> str:
        """Generate a normalized ID from a list of strings.

        Args:
            strings (List[str]): List of strings to combine into an ID.

        Returns:
            str: Normalized ID string (lowercase, hyphen-separated).
        """
        normal_id: str = ""
        for string in strings:
            normal_id += f'{string.lower().replace(" ", "-")}_'
        return normal_id.rstrip("_")
