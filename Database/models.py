from pydantic import BaseModel, Field
from typing import Optional, List

class Article(BaseModel):
    id: Optional[str]
    title: str
    abstract: Optional[str]
    authors: List[str]
    published_date: str

class CrossrefArticleDetails(BaseModel):
    """
    A dataclass representing details about an individual article.

    Attributes:
        tc_count (int): Total citation count for the article.
        faculty_members (list[str]): List of faculty members associated with the article.
        faculty_affiliations (dict[str, list[str]]): Mapping of faculty members to their affiliations.
    """
    _id: str = Field(default="")
    title: str = Field(default="")
    tc_count: int = 0
    faculty_members: list[str] = Field(default_factory=list)
    faculty_affiliations: dict[str, list[str]] = Field(default_factory=dict)
    abstract: str = Field(default="")
    license_url: str = Field(default="")
    date_published_print: str = Field(default="")
    date_published_online: str = Field(default="")
    journal: str = Field(default="")
    download_url: str = Field(default="")
    doi: str = Field(default="")
    