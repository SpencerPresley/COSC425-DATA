from dataclasses import dataclass, field
from typing import Any, Dict, List, Set

from academic_metrics.enums import DataClassTypes
from academic_metrics.factories import DataClassFactory

from .abstract_base_dataclass import AbstractBaseDataClass


@dataclass
@DataClassFactory.register_dataclass(DataClassTypes.CATEGORY_INFO)
class CategoryInfo(AbstractBaseDataClass):
    """
    A dataclass representing information about an academic category.

    This class stores various metrics and details related to an academic category,
    including counts of faculty, departments, and articles, as well as sets of
    related entities and citation information.

    Attributes:
        _id (str): Unique identifier for the category
        url (str): A URL-friendly version of the category name
        category_name (str): Name of the category
        faculty_count (int): Number of faculty members in this category
        department_count (int): Number of departments in this category
        article_count (int): Number of articles in this category
        files (Set[str]): File names associated with this category
        faculty (Set[str]): Faculty names in this category
        departments (Set[str]): Department names in this category
        titles (Set[str]): Article titles in this category
        tc_count (int): Total citation count for articles
        tc_list (List[int]): Individual citation counts for articles
        citation_average (int): Average citations per article
        doi_list (Set[str]): List of DOIs for articles
        themes (Set[str]): Themes associated with this category
    """

    _id: str = ""
    url: str = ""
    category_name: str = ""
    faculty_count: int = 0
    department_count: int = 0
    article_count: int = 0
    files: Set[str] = field(default_factory=set)
    faculty: Set[str] = field(default_factory=set)
    departments: Set[str] = field(default_factory=set)
    titles: Set[str] = field(default_factory=set)
    tc_count: int = 0
    citation_average: int = 0
    doi_list: Set[str] = field(default_factory=set)
    themes: Set[str] = field(default_factory=set)


@dataclass
@DataClassFactory.register_dataclass(DataClassTypes.GLOBAL_FACULTY_STATS)
class GlobalFacultyStats(AbstractBaseDataClass):
    """
    A dataclass representing all of a faculty member's articles across all categories.

    Attributes:
        _id (str): Unique identifier for the faculty member
        name (str): Name of the faculty member
        total_citations (int): Total number of citations across all articles
        article_count (int): Total number of articles
        average_citations (int): Average citations per article
        department_affiliations (Set[str]): All department affiliations
        dois (Set[str]): All DOIs of faculty's articles
        titles (Set[str]): All article titles
        categories (Set[str]): All categories
        category_ids (Set[str]): All category IDs
        top_level_categories (Set[str]): High-level category classifications
        mid_level_categories (Set[str]): Mid-level category classifications
        low_level_categories (Set[str]): Detailed category classifications
        themes (Set[str]): Research themes
        citation_map (Dict[str, int]): Mapping of articles to citation counts
        journals (Set[str]): All journals published in
    """

    _id: str = field(default="")
    name: str = field(default="")
    total_citations: int = 0
    article_count: int = 0
    average_citations: int = 0
    department_affiliations: Set[str] = field(default_factory=set)
    dois: Set[str] = field(default_factory=set)
    titles: Set[str] = field(default_factory=set)
    categories: Set[str] = field(default_factory=set)
    top_level_categories: Set[str] = field(default_factory=set)
    mid_level_categories: Set[str] = field(default_factory=set)
    low_level_categories: Set[str] = field(default_factory=set)
    category_urls: Set[str] = field(default_factory=set)
    top_category_urls: Set[str] = field(default_factory=set)
    mid_category_urls: Set[str] = field(default_factory=set)
    low_category_urls: Set[str] = field(default_factory=set)
    themes: Set[str] = field(default_factory=set)
    citation_map: Dict[str, int] = field(default_factory=dict)
    journals: Set[str] = field(default_factory=set)


@dataclass
@DataClassFactory.register_dataclass(DataClassTypes.FACULTY_INFO)
class FacultyInfo(AbstractBaseDataClass):
    """
    A dataclass representing detailed information about a faculty member.

    Attributes:
        _id (str): Unique identifier for faculty member
        name (str): Faculty member's name
        category (str): Associated category
        category_id (str): Category identifier
        total_citations (int): Total number of citations for all articles
        article_count (int): Number of articles authored
        average_citations (int): Average citations per article
        titles (Set[str]): Set of article titles
        dois (Set[str]): Set of DOIs for articles
        department_affiliations (Set[str]): Departments affiliated with
        doi_citation_map (Dict[str, int]): Maps DOIs to citation counts
    """

    _id: str = field(default="")
    name: str = field(default="")
    category: str = field(default="")
    category_url: str = field(default="")
    total_citations: int = 0
    article_count: int = 0
    average_citations: int = 0
    titles: Set[str] = field(default_factory=set)
    dois: Set[str] = field(default_factory=set)
    department_affiliations: Set[str] = field(default_factory=set)
    doi_citation_map: Dict[str, int] = field(default_factory=dict)


@dataclass
@DataClassFactory.register_dataclass(DataClassTypes.FACULTY_STATS)
class FacultyStats(AbstractBaseDataClass):
    """
    A dataclass representing statistics for all faculty members.

    Attributes:
        faculty_stats (Dict[str, FacultyInfo]): Maps faculty names to their info
    """

    faculty_stats: Dict[str, FacultyInfo] = field(default_factory=dict)

    def refine_faculty_stats(
        self, *, faculty_name_unrefined: str, name_variations: Dict[str, Any]
    ) -> None:
        """
        Refines faculty statistics by updating faculty names based on variations.

        Args:
            faculty_name_unrefined: Original faculty name
            name_variations: Dictionary of name variations
        """
        refined_name = self.get_refined_faculty_name(
            faculty_name_unrefined, name_variations
        )
        if faculty_name_unrefined in self.faculty_stats:
            self.faculty_stats[refined_name] = self.faculty_stats.pop(
                faculty_name_unrefined
            )

    def get_refined_faculty_name(
        self, unrefined_name: str, name_variations: Dict[str, Any]
    ) -> str:
        """
        Gets the refined name for a faculty member.

        Args:
            unrefined_name: Original faculty name
            name_variations: Dictionary of name variations

        Returns:
            Refined faculty name
        """
        for normalized_name, name_variation in name_variations.items():
            if unrefined_name in name_variation.variations:
                return name_variation.most_frequent_variation()
        return unrefined_name

    def set_params(self, params: Dict[str, Any]) -> None:
        """
        Override set_params to handle the nested FacultyInfo dictionary.

        Args:
            params: Dictionary that can include either a full faculty_stats dictionary
                   or direct updates to individual faculty members.

        Examples:
            Case 1 - Full faculty_stats dictionary:
            >>> faculty_stats = DataClassFactory.get_dataclass(DataClassTypes.FACULTY_STATS)
            >>> faculty_stats.set_params({
            ...     "faculty_stats": {
            ...         "Dr. Smith": {"total_citations": 100, "article_count": 5},
            ...         "Dr. Jones": {"total_citations": 50, "article_count": 3}
            ...     }
            ... })

            Case 2 - Direct faculty member updates:
            >>> faculty_stats = DataClassFactory.get_dataclass(DataClassTypes.FACULTY_STATS)
            >>> faculty_stats.set_params({
            ...     "Dr. Smith": {"total_citations": 100, "article_count": 5}
            ... })
        """
        # Case 1: If params contains a full faculty_stats dictionary
        if "faculty_stats" in params:
            faculty_data = params["faculty_stats"]
        # Case 2: If params is direct faculty member data
        else:
            faculty_data = params

        # Update faculty info for each member
        for name, info in faculty_data.items():
            # Create FacultyInfo if it doesn't exist
            if name not in self.faculty_stats:
                self.faculty_stats[name] = DataClassFactory.get_dataclass(
                    DataClassTypes.FACULTY_INFO
                )

            # Update the faculty info
            if isinstance(info, dict):
                self.faculty_stats[name].set_params(info)
            elif isinstance(info, FacultyInfo):
                self.faculty_stats[name] = info


@dataclass
@DataClassFactory.register_dataclass(DataClassTypes.ARTICLE_DETAILS)
class ArticleDetails(AbstractBaseDataClass):
    """
    A dataclass representing details about an individual article.

    Attributes:
        tc_count (int): Total citation count for the article
        faculty_members (Set[str]): Faculty members associated with article
        faculty_affiliations (Dict[str, List[str]]): Maps faculty to affiliations
        abstract (str): Article abstract
        license_url (str): URL to article license
        date_published_print (str): Print publication date
        date_published_online (str): Online publication date
        journal (str): Journal name
        download_url (str): URL to download article
        doi (str): Digital Object Identifier
    """

    tc_count: int = 0
    faculty_members: Set[str] = field(default_factory=set)
    faculty_affiliations: Dict[str, List[str]] = field(default_factory=dict)
    abstract: str = field(default="")
    license_url: str = field(default="")
    date_published_print: str = field(default="")
    date_published_online: str = field(default="")
    journal: str = field(default="")
    download_url: str = field(default="")
    doi: str = field(default="")


@dataclass
@DataClassFactory.register_dataclass(DataClassTypes.ARTICLE_STATS)
class ArticleStats(AbstractBaseDataClass):
    """
    A dataclass representing statistics for all articles.

    Attributes:
        article_citation_map (Dict[str, ArticleDetails]): Maps article titles to details

    Examples:
        >>> article_stats = DataClassFactory.get_dataclass(DataClassTypes.ARTICLE_STATS)
        >>> article_stats.set_params({
        ...     "article_citation_map": {
        ...         "Article Title": {
        ...             "tc_count": 10,
        ...             "faculty_members": {"Dr. Smith", "Dr. Jones"},
        ...             "journal": "Nature"
        ...         }
        ...     }
        ... })
    """

    article_citation_map: Dict[str, ArticleDetails] = field(default_factory=dict)

    def set_params(self, params: Dict[str, Any]) -> None:
        """
        Override set_params to handle the nested ArticleDetails dictionary.

        Args:
            params: Dictionary containing article data

        Examples:
            >>> article_stats = DataClassFactory.get_dataclass(DataClassTypes.ARTICLE_STATS)
            >>> article_stats.set_params({
            ...     "Article Title": {
            ...         "tc_count": 10,
            ...         "faculty_members": {"Dr. Smith"},
            ...         "journal": "Nature"
            ...     }
            ... })
        """
        # Case 1: If params contains a full article_citation_map
        if "article_citation_map" in params:
            article_data = params["article_citation_map"]
        # Case 2: If params is direct article data
        else:
            article_data = params

        # Update article details for each article
        for title, details in article_data.items():
            # Create ArticleDetails if it doesn't exist
            if title not in self.article_citation_map:
                self.article_citation_map[title] = DataClassFactory.get_dataclass(
                    DataClassTypes.ARTICLE_DETAILS
                )

            # Update the article details
            if isinstance(details, dict):
                self.article_citation_map[title].set_params(details)
            elif isinstance(details, ArticleDetails):
                self.article_citation_map[title] = details


@dataclass
@DataClassFactory.register_dataclass(DataClassTypes.CROSSREF_ARTICLE_DETAILS)
class CrossrefArticleDetails(AbstractBaseDataClass):
    """
    A dataclass representing details about an individual article from Crossref.

    Attributes:
        _id (str): Unique identifier
        title (str): Article title
        tc_count (int): Total citation count
        faculty_members (Set[str]): Faculty members associated with article
        faculty_affiliations (Dict[str, List[str]]): Maps faculty to affiliations
        abstract (str): Article abstract
        license_url (str): URL to article license
        date_published_print (str): Print publication date
        date_published_online (str): Online publication date
        journal (str): Journal name
        download_url (str): URL to download article
        doi (str): Digital Object Identifier
        themes (Set[str]): Research themes
        categories (Set[str]): Article categories
        category_ids (Set[str]): Category identifiers
        top_level_categories (Set[str]): High-level categories
        mid_level_categories (Set[str]): Mid-level categories
        low_level_categories (Set[str]): Detailed categories
    """

    _id: str = field(default="")
    title: str = field(default="")
    tc_count: int = 0
    faculty_members: Set[str] = field(default_factory=set)
    faculty_affiliations: Dict[str, List[str]] = field(default_factory=dict)
    abstract: str = field(default="")
    license_url: str = field(default="")
    date_published_print: str = field(default="")
    date_published_online: str = field(default="")
    journal: str = field(default="")
    download_url: str = field(default="")
    doi: str = field(default="")
    themes: Set[str] = field(default_factory=set)
    categories: Set[str] = field(default_factory=set)
    category_urls: Set[str] = field(default_factory=set)
    top_level_categories: Set[str] = field(default_factory=set)
    mid_level_categories: Set[str] = field(default_factory=set)
    low_level_categories: Set[str] = field(default_factory=set)
    top_category_urls: Set[str] = field(default_factory=set)
    mid_category_urls: Set[str] = field(default_factory=set)
    low_category_urls: Set[str] = field(default_factory=set)
    url: str = field(default="")


@dataclass
@DataClassFactory.register_dataclass(DataClassTypes.CROSSREF_ARTICLE_STATS)
class CrossrefArticleStats(AbstractBaseDataClass):
    """
    A dataclass representing statistics for all Crossref articles.

    Attributes:
        article_citation_map (Dict[str, CrossrefArticleDetails]): Maps DOIs to article details

    Examples:
        >>> stats = DataClassFactory.get_dataclass(DataClassTypes.CROSSREF_ARTICLE_STATS)
        >>> stats.set_params({
        ...     "article_citation_map": {
        ...         "10.1234/nature12345": {
        ...             "title": "Research Paper",
        ...             "tc_count": 10,
        ...             "faculty_members": {"Dr. Smith"},
        ...             "themes": {"AI", "ML"}
        ...         }
        ...     }
        ... })
    """

    article_citation_map: Dict[str, CrossrefArticleDetails] = field(
        default_factory=dict
    )

    def set_params(self, params: Dict[str, Any], debug: bool = False) -> None:
        """
        Override set_params to handle the nested CrossrefArticleDetails dictionary.

        Args:
            params: Dictionary containing article data

        Examples:
            >>> stats = DataClassFactory.get_dataclass(DataClassTypes.CROSSREF_ARTICLE_STATS)
            >>> stats.set_params({
            ...     "10.1234/nature12345": {
            ...         "title": "Research Paper",
            ...         "tc_count": 10,
            ...         "faculty_members": {"Dr. Smith"}
            ...     }
            ... })
        """
        if debug:
            print(f"set_params called with params: {params}")
            print(
                f"Current article_citation_map type: {type(self.article_citation_map)}"
            )
            print(f"Current article_citation_map value: {self.article_citation_map}")
        # Case 1: If params contains a full article_citation_map
        if "article_citation_map" in params:
            article_data = params["article_citation_map"]
        # Case 2: If params is direct article data
        else:
            article_data = params

        # Update article details for each DOI
        for doi, details in article_data.items():
            # Create CrossrefArticleDetails if it doesn't exist
            if doi not in self.article_citation_map.keys():
                self.article_citation_map[doi] = DataClassFactory.get_dataclass(
                    DataClassTypes.CROSSREF_ARTICLE_DETAILS
                )

            # Update the article details
            if isinstance(details, dict):
                self.article_citation_map[doi].set_params(details)
            elif isinstance(details, CrossrefArticleDetails):
                self.article_citation_map[doi] = details
