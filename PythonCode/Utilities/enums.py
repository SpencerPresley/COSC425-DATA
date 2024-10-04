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
