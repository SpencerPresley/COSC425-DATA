from enum import Enum


class DataClassTypes(Enum):
    """Enum for the different types of data classes.

    Attributes:
        CATEGORY_INFO (str): Category information.
        GLOBAL_FACULTY_STATS (str): Global faculty statistics.
        FACULTY_INFO (str): Faculty information.
        FACULTY_STATS (str): Faculty statistics.
        ARTICLE_DETAILS (str): Article details.
        ARTICLE_STATS (str): Article statistics.
        CROSSREF_ARTICLE_DETAILS (str): Crossref article details.
        CROSSREF_ARTICLE_STATS (str): Crossref article statistics.
    """

    CATEGORY_INFO = "category_info"
    GLOBAL_FACULTY_STATS = "global_faculty_stats"
    FACULTY_INFO = "faculty_info"
    FACULTY_STATS = "faculty_stats"
    ARTICLE_DETAILS = "article_details"
    ARTICLE_STATS = "article_stats"
    CROSSREF_ARTICLE_DETAILS = "crossref_article_details"
    CROSSREF_ARTICLE_STATS = "crossref_article_stats"
