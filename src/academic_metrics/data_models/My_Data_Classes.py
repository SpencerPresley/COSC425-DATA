from dataclasses import dataclass, field, asdict
from typing import Set, List


@dataclass
class CategoryInfo:
    """
    A dataclass representing information about an academic category.

    This class stores various metrics and details related to an academic category,
    including counts of faculty, departments, and articles, as well as sets of
    related entities and citation information.

    Attributes:
        url (str): A URL-friendly version of the category name.
        faculty_count (int): The number of faculty members in this category.
        department_count (int): The number of departments in this category.
        article_count (int): The number of articles in this category.
        files (Set[str]): A set of file names associated with this category.
        faculty (Set[str]): A set of faculty names in this category.
        departments (Set[str]): A set of department names in this category.
        titles (Set[str]): A set of article titles in this category.
        tc_count (int): Total citation count for articles in this category.
        tc_list (List[int]): A list of individual citation counts for articles.
        citation_average (int): The average number of citations per article.

    Methods:
        to_dict: Converts the dataclass instance to a dictionary suitable for JSON serialization.

    Design:
        Uses Python's dataclass for automatic generation of common methods.
        Utilizes default values and factory methods for mutable default attributes.
        Provides a custom method for dictionary conversion with JSON compatibility.

    Summary:
        Encapsulates all relevant information about an academic category,
        providing a structured way to store and manipulate category-related data.
    """

    url: str = ""
    faculty_count: int = 0
    department_count: int = 0
    article_count: int = 0
    files: Set[str] = field(default_factory=set)
    faculty: Set[str] = field(default_factory=set)
    departments: Set[str] = field(default_factory=set)
    titles: Set[str] = field(default_factory=set)
    tc_count: int = 0
    tc_list: List[int] = field(default_factory=list)
    citation_average: int = 0
    doi_list: Set[str] = field(default_factory=set)

    # this holds the file names associated with articles
    # article_set: Set[str] = field(default_factory=set)

    def to_dict(self, exclude_keys: List[str] = None) -> dict:
        """
        Converts the CategoryInfo instance to a dictionary suitable for JSON serialization.

        This method creates a dictionary representation of the CategoryInfo instance,
        excluding the 'files' attribute and converting all Set instances to lists
        for JSON compatibility.

        Returns:
            dict: A dictionary representation of the CategoryInfo instance.

        Design:
            Uses the asdict utility from dataclasses for initial conversion.
            Excludes the 'files' attribute from the resulting dictionary.
            Converts Set instances to lists for JSON serialization.

        Summary:
            Provides a JSON-serializable dictionary representation of the CategoryInfo instance,
            facilitating data export and storage.
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
            if isinstance(value, Set):
                data_dict[key] = list(value)
        return data_dict
