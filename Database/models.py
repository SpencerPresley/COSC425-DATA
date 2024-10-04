from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class Category(BaseModel):
    url: str = Field(..., description="URL of the category")
    faculty_count: int = Field(
        ..., description="Number of faculty members in the category"
    )
    department_count: int = Field(
        ..., description="Number of departments in the category"
    )
    article_count: int = Field(..., description="Number of articles in the category")
    faculty: List[str] = Field(
        ..., description="List of faculty members in the category"
    )
    departments: List[str] = Field(
        ..., description="List of departments in the category"
    )
    titles: List[str] = Field(..., description="List of article titles in the category")
    tc_count: int = Field(..., description="Total number of citations in the category")
    citation_average: int = Field(
        ..., description="Average number of citations in the category"
    )


class CategoryName(BaseModel):
    name: str = Field(..., description="Name of the category")
    data: Category = Field(..., description="Category data")


class CategoryOut(BaseModel):
    name: str = Field(..., description="Name of the category")
    url: str = Field(..., description="URL of the category")
    faculty_count: int = Field(
        ..., description="Number of faculty members in the category"
    )
    department_count: int = Field(
        ..., description="Number of departments in the category"
    )
    article_count: int = Field(..., description="Number of articles in the category")
    faculty: List[str] = Field(
        ..., description="List of faculty members in the category"
    )
    departments: List[str] = Field(
        ..., description="List of departments in the category"
    )
    titles: List[str] = Field(..., description="List of article titles in the category")
    tc_count: int = Field(..., description="Total number of citations in the category")
    citation_average: int = Field(
        ..., description="Average number of citations in the category"
    )
