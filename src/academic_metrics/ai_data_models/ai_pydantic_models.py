from typing import List

from pydantic import BaseModel, Field


class Feedback(BaseModel):
    assistant_name: str
    feedback: str


class Classification(BaseModel):
    categories: List[str]
    reasoning: str
    confidence_score: float


class MethodDetail(BaseModel):
    reasoning: str
    passages: List[str]
    confidence_score: float


class MethodExtractionOutput(BaseModel):
    methods: List[str]
    method_details: dict[str, MethodDetail]


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
    reasoning: str
    feedback: List[Feedback]


class ClassificationOutput(BaseModel):
    classifications: List[Classification]
    reflection: str
    feedback: List[Feedback]


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
    individual_themes_analysis: List[IndividualThemeAnalysis] = (
        Field(..., description="Detailed analysis for each identified theme"),
    )
    reflection: str = Field(
        ...,
        description="Detailed reflection on your process of identifying the themes present in the abstract",
    )
    challenges: str = Field(
        ...,
        description="Detailed explanation of the challenges you faced in identifying the themes present in the abstract and what could be done to help you in the future. If you did not face any challenges, simply provide 'No challenges faced'",
    )
