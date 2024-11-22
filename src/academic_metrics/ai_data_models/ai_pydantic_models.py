from typing import List

from pydantic import BaseModel, Field


class Feedback(BaseModel):
    assistant_name: str
    feedback: str


class Classification(BaseModel):
    categories: List[str]


class MethodDetail(BaseModel):
    reasoning: str
    passages: List[str]
    confidence_score: float


class MethodExtractionOutput(BaseModel):
    methods: List[str]


class SentenceDetails(BaseModel):
    sentence: str
    meaning: str
    reasoning: str
    confidence_score: float


class AbstractSentenceAnalysis(BaseModel):
    sentence_details: List[SentenceDetails]
    overall_theme: str
    summary: str


class AbstractSummary(BaseModel):
    summary: str


class ClassificationOutput(BaseModel):
    classifications: List[Classification]


class IndividualThemeAnalysis(BaseModel):
    theme: str = (Field(..., description="The theme you are analyzing"),)
    reasoning: str = (
        Field(
            ...,
            description="Detailed reasoning for why this theme is present in the abstract",
        ),
    )
    confidence_score: float = (
        Field(..., description="Confidence score for the identified theme"),
    )
    supporting_passages: List[str] = (
        Field(
            ...,
            description="List of passages from the abstract which support the identification of this theme",
        ),
    )
    abstract_summary_alignment: str = (
        Field(..., description="How this theme aligns with the abstract summary"),
    )
    methodologies_justification: str = Field(
        ...,
        description="A justification for why this identified theme was not selected due to the methodologies present in the abstract",
    )


class ThemeAnalysis(BaseModel):
    themes: List[str] = (
        Field(..., description="List of all themes identified in the abstract"),
    )
