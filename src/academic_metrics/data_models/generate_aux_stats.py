# Python 3.9.5
# PythonCode/Utilities/generate_aux_stats.py

# This script will generate auxiliary statistics for the WoS data
# such as influential faculty, influential articles, etc.

# Python libraries
import json
from dataclasses import dataclass, field, asdict
from typing import Set, List, Any

# Custom libraries
from academic_metrics.utils import Utilities


class GenerateAuxStats:
    """
    A class for generating auxiliary statistics from Web of Science (WoS) data.

    This class processes WoS data to generate various auxiliary statistics,
    including information about influential faculty and articles.

    Attributes:
        utils (Utilities): An instance of the Utilities class for helper functions.
        split_files_path (str): Path to the directory containing split WoS data files.
        cat_data (dict[str, Any]): A dictionary of category data, where Any is actually a CategoryInfo object.
        aux_stats (dict[str, Any]): A dictionary to store generated auxiliary statistics.

    Note:
        The 'Any' type hint for cat_data is used to avoid circular imports. In practice,
        this is a CategoryInfo object from the My_Data_Classes module.

    Methods:
        get_aux_stats_dict: Returns a dictionary of auxiliary statistics.
        generate_aux_stats: Generates auxiliary statistics from the given path.
        generate_influential_faculty: Generates statistics about influential faculty.
        generate_influential_articles: Generates statistics about influential articles.

    Design:
        Provides a framework for generating various auxiliary statistics from WoS data.
        Uses static methods for specific statistic generation tasks.

    Summary:
        Facilitates the generation and organization of auxiliary statistics from WoS data,
        focusing on influential faculty and articles.
    """

    def __init__(self, *, split_files_path: str, cat_data: dict[str, Any]):
        """
        Initializes the GenerateAuxStats instance.

        Args:
            split_files_path (str): Path to the directory containing split WoS data files.
            cat_data (dict[str, Any]): A dictionary of category data, where Any is actually a CategoryInfo object.

        Note:
            The 'Any' type hint for cat_data is used to avoid circular imports. In practice,
            this is a CategoryInfo object from the My_Data_Classes module.
        """
        self.utils = Utilities()
        self.split_files_path: str = split_files_path
        self.cat_data: dict[str, Any] = cat_data
        self.aux_stats: dict[str, Any] = {}

    # returns a dictionary of auxiliary statistics
    def get_aux_stats_dict():
        pass

    # Methods to generate auxiliary statistics
    @staticmethod
    def generate_aux_stats(path: str):
        pass

    @staticmethod
    def generate_influential_faculty():
        pass

    @staticmethod
    def generate_influential_articles():
        pass


@dataclass
class FacultyArticleStats:
    """
    A dataclass representing statistics about a faculty member's articles.

    Attributes:
        article_citation_map (dict[str, int]): A mapping of article titles to their citation counts.
    """

    article_citation_map: dict[str, int] = field(default_factory=dict)


@dataclass
class GlobalFacultyStats:
    """
    A dataclass representing all of a faculty member's articles across all categories.
    """

    name: str = field(default="")
    total_citations: int = 0
    article_count: int = 0
    average_citations: int = 0
    department_affiliations: set[str] = field(default_factory=set)
    dois: set[str] = field(default_factory=set)
    titles: set[str] = field(default_factory=set)
    categories: set[str] = field(default_factory=set)
    top_level_categories: set[str] = field(default_factory=set)
    mid_level_categories: set[str] = field(default_factory=set)
    low_level_categories: set[str] = field(default_factory=set)
    themes: set[str] = field(default_factory=set)
    citation_map: dict[str, int] = field(default_factory=dict)
    journals: set[str] = field(default_factory=set)

    def to_dict(self):
        """Convert the dataclass to a dictionary, converting sets to lists for JSON serialization."""
        # Convert sets to lists for JSON serialization
        for key, value in self.__dict__.items():
            if isinstance(value, set):
                self.__dict__[key] = list(value)

        return {
            "name": self.name,
            "total_citations": self.total_citations,
            "article_count": self.article_count,
            "average_citations": self.average_citations,
            "department_affiliations": list(self.department_affiliations),
            "dois": list(self.dois),
            "titles": list(self.titles),
            "categories": list(self.categories),
            "top_level_categories": list(self.top_level_categories),
            "mid_level_categories": list(self.mid_level_categories),
            "low_level_categories": list(self.low_level_categories),
            "themes": list(self.themes),
            "citation_map": self.citation_map,
            "journals": list(self.journals),
        }


@dataclass
class FacultyInfo:
    """
    A dataclass representing detailed information about a faculty member.

    Attributes:
        total_citations (int): Total number of citations for all articles.
        article_count (int): Number of articles authored by the faculty member.
        average_citations (int): Average number of citations per article.
        department_affiliations (list[str]): List of departments the faculty is affiliated with.
        doi_citation_map (dict[str, int]): Detailed citation information for each article.
    """

    total_citations: int = 0
    article_count: int = 0
    average_citations: int = 0
    titles: set[str] = field(default_factory=set)
    dois: set[str] = field(default_factory=set)
    department_affiliations: set[str] = field(default_factory=set)
    doi_citation_map: dict[str, int] = field(default_factory=dict)


@dataclass
class FacultyStats:
    """
    A dataclass representing statistics for all faculty members.

    Attributes:
        faculty_stats (dict[str, FacultyInfo]): A mapping of faculty names to their detailed information.

    Methods:
        refine_faculty_stats: Refines faculty statistics based on name variations.
        get_refined_faculty_name: Gets the refined name for a faculty member.
        to_dict: Converts the dataclass instance to a dictionary suitable for JSON serialization.
    """

    faculty_stats: dict[str, FacultyInfo] = field(default_factory=dict)

    def refine_faculty_stats(
        self, *, faculty_name_unrefined: str, name_variations: dict[str, Any]
    ):
        """
        Refines faculty statistics by updating the faculty name based on name variations.

        Args:
            faculty_name_unrefined (str): The original, unrefined faculty name.
            name_variations (dict[str, Any]): A dictionary of name variations, where Any is a NameVariation object.

        Note:
            The 'Any' type hint for name_variations is used to avoid circular imports. In practice,
            this is a NameVariation object from another module.
        """
        # grab the normalized name for the unrefined variation
        refined_faculty_name = self.get_refined_faculty_name(
            faculty_name_unrefined, name_variations
        )

        # update dictionary key from unrefined name to refined name
        self.faculty_stats[refined_faculty_name] = self.faculty_stats.pop(
            faculty_name_unrefined
        )

    def get_refined_faculty_name(self, unrefined_name, name_variations):
        """
        Gets the refined name for a faculty member based on name variations.

        Args:
            unrefined_name (str): The original, unrefined faculty name.
            name_variations (dict[str, Any]): A dictionary of name variations, where Any is a NameVariation object.

        Returns:
            str: The refined faculty name.

        Note:
            The 'Any' type hint for name_variations is used to avoid circular imports. In practice,
            this is a NameVariation object from another module.
        """
        # Iterate over each normalized name and its corresponding NameVariation object
        for normalized_name, name_variation in name_variations.items():
            # Check if the unrefined name is a variation in the NameVariation object
            if unrefined_name in name_variation.variations:
                # Return the most frequent variation as the refined name
                return name_variation.most_frequent_variation()
        # If no matching variation is found, return the unrefined name as a fallback
        return unrefined_name

    def to_dict(self) -> dict[str, dict]:
        """
        Converts FacultyStats to a dictionary suitable for JSON serialization.
        Automatically converts sets to lists.

        Returns:
            dict[str, dict]: Dictionary of faculty info with faculty names as keys
        """
        faculty_dict = {}
        for faculty_name, info in self.faculty_stats.items():
            faculty_dict[faculty_name] = {
                "total_citations": info.total_citations,
                "article_count": info.article_count,
                "average_citations": info.average_citations,
                "department_affiliations": list(info.department_affiliations),
                "dois": list(info.dois),
                "titles": list(info.titles),
                "citation_map": info.doi_citation_map,
            }
        return faculty_dict


@dataclass
class ArticleDetails:
    """
    A dataclass representing details about an individual article.

    Attributes:
        tc_count (int): Total citation count for the article.
        faculty_members (list[str]): List of faculty members associated with the article.
        faculty_affiliations (dict[str, list[str]]): Mapping of faculty members to their affiliations.
    """

    tc_count: int = 0
    faculty_members: set[str] = field(default_factory=set)
    faculty_affiliations: dict[str, list[str]] = field(default_factory=dict)
    abstract: str = field(default="")
    license_url: str = field(default="")
    date_published_print: str = field(default="")
    date_published_online: str = field(default="")
    journal: str = field(default="")
    download_url: str = field(default="")
    doi: str = field(default="")


@dataclass
class ArticleStats:
    """
    A dataclass representing statistics for all articles.

    Attributes:
        article_citation_map (dict[str, ArticleDetails]): A mapping of article titles to their detailed information.

    Methods:
        to_dict: Converts the dataclass instance to a dictionary suitable for JSON serialization.
    """

    article_citation_map: dict[str, ArticleDetails] = field(default_factory=dict)

    def to_dict(self, exclude_keys: List[str] = None) -> dict:
        """
        Converts the ArticleStats instance to a dictionary suitable for JSON serialization.

        Returns:
            dict: A dictionary representation of the ArticleStats instance.
        """

        # Utilize asdict utility from dataclasses, then change sets to lists
        data_dict = asdict(self)

        # Exclude 'files' from the dictionary
        if exclude_keys is not None:
            for key in exclude_keys:
                if key in data_dict:
                    del data_dict[key]

        # Convert sets to lists for JSON serialization
        for key, value in data_dict.items():
            if isinstance(value, set):
                data_dict[key] = list(value)
        return data_dict


@dataclass
class CrossrefArticleDetails:
    """
    A datalass representing details about an individual article.

    Attributes:
        tc_count (int): Total citation count for the article.
        faculty_members (list[str]): List of faculty members associated with the article.
        faculty_affiliations (dict[str, list[str]]): Mapping of faculty members to their affiliations.
    """

    title: str = field(default="")
    tc_count: int = 0
    faculty_members: set[str] = field(default_factory=set)
    faculty_affiliations: dict[str, list[str]] = field(default_factory=dict)
    abstract: str = field(default="")
    license_url: str = field(default="")
    date_published_print: str = field(default="")
    date_published_online: str = field(default="")
    journal: str = field(default="")
    download_url: str = field(default="")
    doi: str = field(default="")
    themes: set[str] = field(default_factory=set)
    categories: set[str] = field(default_factory=set)
    top_level_categories: set[str] = field(default_factory=set)
    mid_level_categories: set[str] = field(default_factory=set)
    low_level_categories: set[str] = field(default_factory=set)


@dataclass
class CrossrefArticleStats:
    """
    A dataclass representing statistics for all articles.

    Attributes:
        article_citation_map (dict[str, CrossrefArticleDetails]): A mapping of article dois to their detailed information.

    Methods:
        to_dict: Converts the dataclass instance to a dictionary suitable for JSON serialization.
    """

    article_citation_map: dict[str, CrossrefArticleDetails] = field(
        default_factory=dict
    )

    def to_dict(self, exclude_keys: List[str] = None) -> dict:
        """
        Converts the ArticleStats instance to a dictionary suitable for JSON serialization.

        Returns:
            dict: A dictionary representation of the ArticleStats instance.
        """

        # Utilize asdict utility from dataclasses, then change sets to lists
        data_dict = asdict(self)

        # Exclude 'files' from the dictionary
        if exclude_keys is not None:
            for key in exclude_keys:
                if key in data_dict:
                    del data_dict[key]

        # Convert sets to lists for JSON serialization
        for key, value in data_dict.items():
            if isinstance(value, set):
                data_dict[key] = list(value)
        return data_dict
