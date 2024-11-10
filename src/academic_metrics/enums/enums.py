from enum import Enum


class AttributeTypes(Enum):
    AUTHOR = "author"
    TITLE = "title"
    ABSTRACT = "abstract"
    END_RECORD = "end_record"
    WC_PATTERN = "wc_pattern"
    DEPARTMENT = "department"
    CROSSREF_TITLE = "crossref-title"
    CROSSREF_ABSTRACT = "crossref-abstract"
    CROSSREF_AUTHORS = "crossref-authors"
    CROSSREF_DEPARTMENTS = "crossref-departments"
    CROSSREF_CATEGORIES = "crossref-categories"
    CROSSREF_CITATION_COUNT = "crossref-citation-count"
    CROSSREF_LICENSE_URL = "crossref-license-url"
    CROSSREF_PUBLISHED_PRINT = "crossref-published-print"
    CROSSREF_CREATED_DATE = "crossref-created-date"
    CROSSREF_PUBLISHED_ONLINE = "crossref-published-online"
    CROSSREF_JOURNAL = "crossref-journal"
    CROSSREF_URL = "crossref-url"
    CROSSREF_DOI = "crossref-doi"
    CROSSREF_THEMES = "crossref-themes"
