from __future__ import annotations
from urllib.parse import quote

from typing import TYPE_CHECKING, List, Any
import logging
import os

if TYPE_CHECKING:
    from academic_metrics.dataclass_models import (
        CategoryInfo,
        FacultyStats,
        GlobalFacultyStats,
        CrossrefArticleStats,
    )
    from academic_metrics.utils import Utilities
    from academic_metrics.utils import WarningManager
    from academic_metrics.factories import DataClassFactory

from academic_metrics.enums import AttributeTypes, DataClassTypes


class CategoryProcessor:
    def __init__(
        self,
        utils: Utilities,
        dataclass_factory: DataClassFactory,
        warning_manager: WarningManager,
    ):
        # Set up logger
        current_dir = os.path.dirname(os.path.abspath(__file__))
        log_file_path = os.path.join(current_dir, "category_processor.log")
        self.logger = logging.getLogger(__name__)
        self.logger.handlers = []
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.FileHandler(log_file_path)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        self.utils: Utilities = utils
        self.warning_manager: WarningManager = warning_manager
        self.dataclass_factory: DataClassFactory = dataclass_factory
        self.category_data: dict[str, CategoryInfo] = {}

        # influential stats dictionaries
        self.faculty_stats: dict[str, FacultyStats] = {}
        self.global_faculty_stats: dict[str, GlobalFacultyStats] = {}
        self.article_stats: dict[str, CrossrefArticleStats] = {}
        self.article_stats_obj = self.dataclass_factory.get_dataclass(
            DataClassTypes.CROSSREF_ARTICLE_STATS
        )

    def process_data_list(self, data: list[dict]) -> None:
        for item in data:
            # Get base attributes
            raw_attributes = self.call_get_attributes(data=item)

            # Get category information
            category_levels = self.initialize_categories(
                raw_attributes.get("categories", [])
            )

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
                "all_categories": category_levels.get("all_categories", []),
                "top_level_categories": category_levels.get("top_level_categories", []),
                "mid_level_categories": category_levels.get("mid_level_categories", []),
                "low_level_categories": category_levels.get("low_level_categories", []),
            }

            self.update_category_stats(**kwargs)
            self.update_faculty_stats(**kwargs)
            self.update_global_faculty_stats(**kwargs)
            self.update_article_stats(**kwargs)
            self.update_article_stats_obj(**kwargs)

    def call_get_attributes(self, *, data):
        attribute_results = self.utils.get_attributes(
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

        if attribute_results[AttributeTypes.CROSSREF_CATEGORIES][0]:
            categories = attribute_results[AttributeTypes.CROSSREF_CATEGORIES][1]
        else:
            raise Exception(f"No category found for data: {data}")

        faculty_members = (
            attribute_results[AttributeTypes.CROSSREF_AUTHORS][1]
            if attribute_results[AttributeTypes.CROSSREF_AUTHORS][0]
            else None
        )
        faculty_affiliations = (
            attribute_results[AttributeTypes.CROSSREF_DEPARTMENTS][1]
            if attribute_results[AttributeTypes.CROSSREF_DEPARTMENTS][0]
            else None
        )
        title = (
            attribute_results[AttributeTypes.CROSSREF_TITLE][1]
            if attribute_results[AttributeTypes.CROSSREF_TITLE][0]
            else None
        )
        tc_count = (
            attribute_results[AttributeTypes.CROSSREF_CITATION_COUNT][1]
            if attribute_results[AttributeTypes.CROSSREF_CITATION_COUNT][0]
            else None
        )
        abstract = (
            attribute_results[AttributeTypes.CROSSREF_ABSTRACT][1]
            if attribute_results[AttributeTypes.CROSSREF_ABSTRACT][0]
            else None
        )
        license_url = (
            attribute_results[AttributeTypes.CROSSREF_LICENSE_URL][1]
            if attribute_results[AttributeTypes.CROSSREF_LICENSE_URL][0]
            else None
        )
        date_published_print = (
            attribute_results[AttributeTypes.CROSSREF_PUBLISHED_PRINT][1]
            if attribute_results[AttributeTypes.CROSSREF_PUBLISHED_PRINT][0]
            else None
        )
        date_published_online = (
            attribute_results[AttributeTypes.CROSSREF_PUBLISHED_ONLINE][1]
            if attribute_results[AttributeTypes.CROSSREF_PUBLISHED_ONLINE][0]
            else None
        )
        journal = (
            attribute_results[AttributeTypes.CROSSREF_JOURNAL][1]
            if attribute_results[AttributeTypes.CROSSREF_JOURNAL][0]
            else None
        )
        download_url = (
            attribute_results[AttributeTypes.CROSSREF_URL][1]
            if attribute_results[AttributeTypes.CROSSREF_URL][0]
            else None
        )
        doi = (
            attribute_results[AttributeTypes.CROSSREF_DOI][1]
            if attribute_results[AttributeTypes.CROSSREF_DOI][0]
            else None
        )
        themes = (
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

    def update_category_stats(self, **kwargs):
        for category in kwargs["all_categories"]:
            category_info = self.category_data[category]
            category_info.set_params(
                {
                    "_id": self._generate_url(category),
                    "url": self._generate_url(category),
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

    def update_faculty_stats(self, **kwargs):
        """Updates faculty stats for each category"""
        for category in kwargs["all_categories"]:
            if category not in self.faculty_stats:
                self.faculty_stats[category] = self.dataclass_factory.get_dataclass(
                    DataClassTypes.FACULTY_STATS,
                )

            for faculty_member in kwargs["faculty_members"]:
                faculty_data = {
                    "_id": self._generate_normal_id(strings=[faculty_member, category]),
                    "name": faculty_member,
                    "category": category,
                    "category_url": self._generate_url(category),
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

    def update_global_faculty_stats(self, **kwargs):
        for faculty_member in kwargs["faculty_members"]:
            if faculty_member not in self.global_faculty_stats:
                self.global_faculty_stats[faculty_member] = (
                    self.dataclass_factory.get_dataclass(
                        DataClassTypes.GLOBAL_FACULTY_STATS, name=faculty_member
                    )
                )

            global_stats = self.global_faculty_stats[faculty_member]
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
                    "category_urls": [
                        self._generate_url(category)
                        for category in kwargs["all_categories"]
                    ],
                    "top_level_categories": kwargs["top_level_categories"],
                    "mid_level_categories": kwargs["mid_level_categories"],
                    "low_level_categories": kwargs["low_level_categories"],
                    "themes": kwargs["themes"],
                    "journals": kwargs["journal"],
                    "citation_map": {kwargs["doi"]: kwargs["tc_count"]},
                }
            )

    def update_article_stats(self, **kwargs):
        for category in kwargs["all_categories"]:
            if category not in self.article_stats:
                self.article_stats[category] = self.dataclass_factory.get_dataclass(
                    DataClassTypes.CROSSREF_ARTICLE_STATS
                )

            article_data = {
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
                "category_urls": [
                    self._generate_url(category)
                    for category in kwargs["all_categories"]
                ],
                "top_level_categories": kwargs["top_level_categories"],
                "mid_level_categories": kwargs["mid_level_categories"],
                "low_level_categories": kwargs["low_level_categories"],
                "url": self._generate_url(kwargs["doi"]),
            }

            self.article_stats[category].set_params({kwargs["doi"]: article_data})

    def update_article_stats_obj(self, **kwargs):
        article_data = {
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
            "category_urls": [
                self._generate_url(cat) for cat in kwargs["all_categories"]
            ],
            "top_level_categories": kwargs["top_level_categories"],
            "mid_level_categories": kwargs["mid_level_categories"],
            "low_level_categories": kwargs["low_level_categories"],
            "url": self._generate_url(kwargs["doi"]),
        }

        self.article_stats_obj.set_params({kwargs["doi"]: article_data})

    def clean_faculty_affiliations(self, faculty_affiliations):
        department_affiliations: dict[str, str] = {}
        for faculty_member, affiliations in faculty_affiliations.items():
            department_affiliations[faculty_member] = affiliations
        return department_affiliations

    def clean_faculty_members(self, faculty_members):
        clean_faculty_members: list[str] = []
        for faculty_member in faculty_members:
            if faculty_member != "":
                clean_faculty_members.append(faculty_member)
        return clean_faculty_members

    def initialize_categories(self, categories):
        top_level_categories = []
        mid_level_categories = []
        low_level_categories = []
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

    def get_faculty_stats(self):
        return self.faculty_stats

    @staticmethod
    def _collect_all_affiliations(faculty_affiliations):
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
    def _generate_url(string: str):
        return quote(string)

    @staticmethod
    def _generate_normal_id(strings: list[str]):
        normal_id = ""
        for string in strings:
            normal_id += f'{string.lower().replace(" ", "-")}_'
        return normal_id.rstrip("_")
