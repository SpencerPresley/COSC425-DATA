from enum import Enum


class AttributeTypes(Enum):
    """Enum for the different types of attributes.

    Attributes:
        AUTHOR (str): Author.
        TITLE (str): Title.
        ABSTRACT (str): Abstract.
        END_RECORD (str): End record.
        WC_PATTERN (str): Word count pattern.
        DEPARTMENT (str): Department.
        CROSSREF_TITLE (str): Crossref title.
        CROSSREF_ABSTRACT (str): Crossref abstract.
        CROSSREF_AUTHORS (str): Crossref authors.
        CROSSREF_DEPARTMENTS (str): Crossref departments.
        CROSSREF_CATEGORIES (str): Crossref categories.
        CROSSREF_URL (str): Crossref URL.
        CROSSREF_CITATION_COUNT (str): Crossref citation count.
        CROSSREF_LICENSE_URL (str): Crossref license URL.
        CROSSREF_PUBLISHED_PRINT (str): Crossref published print.
        CROSSREF_CREATED_DATE (str): Crossref created date.
        CROSSREF_PUBLISHED_ONLINE (str): Crossref published online.
        CROSSREF_JOURNAL (str): Crossref journal.
        CROSSREF_DOI (str): Crossref DOI.
        CROSSREF_THEMES (str): Crossref themes.
        CROSSREF_EXTRA_CONTEXT (str): Crossref extra context.
    """

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
    CROSSREF_EXTRA_CONTEXT = "crossref-extra-context"
