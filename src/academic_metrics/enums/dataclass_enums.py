from enum import Enum


class DataClassTypes(Enum):
    CATEGORY_INFO = "category_info"
    GLOBAL_FACULTY_STATS = "global_faculty_stats"
    FACULTY_INFO = "faculty_info"
    FACULTY_STATS = "faculty_stats"
    ARTICLE_DETAILS = "article_details"
    ARTICLE_STATS = "article_stats"
    CROSSREF_ARTICLE_DETAILS = "crossref_article_details"
    CROSSREF_ARTICLE_STATS = "crossref_article_stats"
