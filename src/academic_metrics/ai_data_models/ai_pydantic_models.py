from typing import List

from pydantic import BaseModel, Field


class Feedback(BaseModel):
    """Model for storing feedback about AI assistant interactions.

    Attributes:
        assistant_name (str): Name of the AI assistant providing feedback
        feedback (str): The actual feedback content
    """

    assistant_name: str
    feedback: str


class Classification(BaseModel):
    """Model for storing category classifications.

    Attributes:
        categories (List[str]): List of assigned category names
            Type: List[str]
    """

    categories: List[str]


class MethodDetail(BaseModel):
    """Model for storing detailed information about extracted methods.

    Attributes:
        reasoning (str): Explanation for why this method was identified
        passages (List[str]): Relevant text passages supporting the method identification
            Type: List[str]
        confidence_score (float): Confidence level in the method identification
            Type: float
    """

    reasoning: str
    passages: List[str]
    confidence_score: float


class MethodExtractionOutput(BaseModel):
    """Model for storing the final output of method extraction.

    Attributes:
        methods (List[str]): List of extracted research methods
            Type: List[str]
    """

    methods: List[str]


class SentenceDetails(BaseModel):
    """Model for storing detailed analysis of individual sentences.

    Attributes:
        sentence (str): The original sentence text
        meaning (str): Interpreted meaning of the sentence
        reasoning (str): Explanation for the interpretation
        confidence_score (float): Confidence level in the analysis
            Type: float
    """

    sentence: str
    meaning: str
    reasoning: str
    confidence_score: float


class AbstractSentenceAnalysis(BaseModel):
    """Model for storing complete sentence-by-sentence analysis of an abstract.

    Attributes:
        sentence_details (List[SentenceDetails]): Detailed analysis of each sentence
            Type: List[:class:`academic_metrics.ai_data_models.ai_pydantic_models.SentenceDetails`]
        overall_theme (str): Main theme identified from all sentences
        summary (str): Brief summary of the entire analysis
    """

    sentence_details: List[SentenceDetails]
    overall_theme: str
    summary: str


class AbstractSummary(BaseModel):
    """Model for storing the condensed summary of an abstract.

    Attributes:
        summary (str): Condensed version of the abstract maintaining key points
    """

    summary: str


class ClassificationOutput(BaseModel):
    """Model for storing the output of taxonomy classification.

    Attributes:
        classifications (List[Classification]): List of category classifications
            Type: List[:class:`academic_metrics.ai_data_models.ai_pydantic_models.Classification`]
    """

    classifications: List[Classification]


class IndividualThemeAnalysis(BaseModel):
    """Model for storing detailed analysis of a single theme.

    Attributes:
        theme (str): The theme being analyzed
        reasoning (str): Detailed reasoning for theme identification
        confidence_score (float): Confidence level in theme identification
            Type: float
        supporting_passages (List[str]): Text passages supporting theme identification
            Type: List[str]
        abstract_summary_alignment (str): Theme alignment with abstract summary
        methodologies_justification (str): Justification based on abstract methodologies
    """

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
    """Model for storing the complete theme analysis of an abstract.

    Attributes:
        themes (List[str]): List of all identified themes
            Type: List[str]
    """

    themes: List[str] = (
        Field(..., description="List of all themes identified in the abstract"),
    )
