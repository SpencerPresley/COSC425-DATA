from __future__ import annotations

import json
import logging
import os
import traceback
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Self, Tuple, Union, cast

from academic_metrics.ai_data_models.ai_pydantic_models import (
    AbstractSentenceAnalysis,
    AbstractSummary,
    ClassificationOutput,
    MethodExtractionOutput,
    ThemeAnalysis,
)
from academic_metrics.ai_prompts.abstract_summary_prompts import (
    ABSTRACT_SUMMARY_SYSTEM_MESSAGE,
    SUMMARY_JSON_STRUCTURE,
)
from academic_metrics.ai_prompts.classification_prompts import (
    CLASSIFICATION_JSON_FORMAT,
    CLASSIFICATION_SYSTEM_MESSAGE,
    TAXONOMY_EXAMPLE,
)
from academic_metrics.ai_prompts.human_prompt import HUMAN_MESSAGE_PROMPT
from academic_metrics.ai_prompts.method_prompts import (
    METHOD_EXTRACTION_CORRECT_EXAMPLE_JSON,
    METHOD_EXTRACTION_INCORRECT_EXAMPLE_JSON,
    METHOD_EXTRACTION_SYSTEM_MESSAGE,
    METHOD_JSON_FORMAT,
)
from academic_metrics.ai_prompts.sentence_analysis_prompts import (
    ABSTRACT_SENTENCE_ANALYSIS_SYSTEM_MESSAGE,
    SENTENCE_ANALYSIS_JSON_EXAMPLE,
)
from academic_metrics.ai_prompts.theme_prompts import (
    THEME_RECOGNITION_JSON_FORMAT,
    THEME_RECOGNITION_SYSTEM_MESSAGE,
)
from academic_metrics.ChainBuilder import ChainManager
from academic_metrics.configs import (
    configure_logging,
    DEBUG,
    LOG_TO_CONSOLE,
)

if TYPE_CHECKING:
    from academic_metrics.utils.taxonomy_util import Taxonomy


class AbstractClassifier:
    """A class for processing research paper abstracts through AI-powered
    analysis and classification.

    This class manages a complete pipeline for analyzing academic paper abstracts, including:
    - Method extraction from abstracts
    - Sentence-by-sentence analysis
    - Abstract summarization
    - Hierarchical taxonomy classification
    - Theme recognition and analysis

    The pipeline uses three separate chain managers for different stages of processing:
    1. Pre-classification: Method extraction, sentence analysis, and summarization
    2. Classification: Hierarchical taxonomy classification
    3. Theme Recognition: Theme identification and analysis

    Attributes:
        Public:
            classification_results (Dict[str, Dict]): Processed results by DOI, containing categories and themes
            raw_classification_outputs (List[Dict]): Raw outputs from the classification chain
            raw_theme_outputs (Dict[str, Dict]): Raw theme analysis results by DOI

        Private:
            _taxonomy (Taxonomy): Taxonomy instance containing the classification hierarchy
            _pre_classification_model (str): Model name for pre-classification tasks
            _classification_model (str): Model name for classification tasks
            _theme_model (str): Model name for theme recognition tasks
            logger (logging.Logger): Logger instance for this class
            banned_categories (List[str]): Categories to exclude from classification
            api_key (str): API key for LLM access
            doi_to_abstract_dict (Dict[str, str]): Mapping of DOIs to abstract texts
            extra_context (Dict[str, Any]): Additional context for classification
            max_classification_retries (int): Maximum retries for failed classifications

    Methods:
        Public Methods:
            classify(): Process all abstracts through the complete pipeline
            get_classification_results_by_doi(doi, return_type): Get results for a specific DOI
            get_raw_classification_outputs(): Get all raw classification outputs
            get_raw_theme_results(): Get all raw theme analysis results
            save_classification_results(output_path): Save processed results to JSON
            save_raw_classification_results(output_path): Save raw classification outputs
            save_raw_theme_results(output_path): Save raw theme results

        Private Methods:
            _run_initial_api_key_validation(api_key): Validate API key format
            _initialize_chain_manager(): Create new chain manager instance
            _add_*_layer(): Add specific processing layers to chain managers
            classify_abstract(abstract, doi, ...): Process single abstract
            extract_classified_categories(output): Extract categories from output

    Examples:
        >>> # Initialize with required components
        >>> taxonomy = Taxonomy()
        >>> abstracts = {
        ...     "10.1234/example": "This is a sample abstract...",
        ...     "10.5678/sample": "Another research abstract..."
        ... }
        >>> api_key = "your-api-key"
        >>> 
        >>> # Create classifier instance
        >>> classifier = AbstractClassifier(
        ...     taxonomy=taxonomy,
        ...     doi_to_abstract_dict=abstracts,
        ...     api_key=api_key
        ... )
        >>> 
        >>> # Run classification pipeline
        >>> classifier.classify()
        >>> 
        >>> # Access results
        >>> results = classifier.get_classification_results_by_doi("10.1234/example")
        >>> print(results["top_categories"])  # View top-level categories
        >>> 
        >>> # Save results
        >>> classifier.save_classification_results("results/classifications.json")\\
        ...     .save_raw_theme_results("results/themes.json")\\
        ...     .save_raw_classification_results("results/raw_outputs.json")
    """

    def __init__(
        self,
        taxonomy: Taxonomy,
        doi_to_abstract_dict: Dict[str, str],
        api_key: str,
        log_to_console: bool | None = LOG_TO_CONSOLE,
        extra_context: Dict[str, Any] | None = None,
        pre_classification_model: str | None = "gpt-4o-mini",
        classification_model: str | None = "gpt-4o-mini",
        theme_model: str | None = "gpt-4o-mini",
        max_classification_retries: int | None = 3,
    ) -> None:
        """Initializes a new AbstractClassifier instance.

        Sets up the complete classification pipeline including chain managers for pre-classification,
        classification, and theme recognition. Initializes data structures for storing results and
        configures logging.

        Args:
            taxonomy: Taxonomy instance containing the hierarchical category structure.
            doi_to_abstract_dict: Dictionary mapping DOIs to their abstract texts.
            api_key: API key for accessing the language model service.
            log_to_console: Whether to output logs to console.
                Defaults to LOG_TO_CONSOLE config value.
            extra_context: Additional context for classification.
                Defaults to None.
            pre_classification_model: Model name for pre-classification tasks.
                Defaults to "gpt-4o-mini".
            classification_model: Model name for classification tasks.
                Defaults to "gpt-4o-mini".
            theme_model: Model name for theme recognition tasks.
                Defaults to "gpt-4o-mini".
            max_classification_retries: Maximum attempts for failed classifications.
                Defaults to 3.

        Raises:
            ValueError: If api_key is empty or invalid.
            TypeError: If api_key cannot be converted to string.

        Note:
            The initialization process:

            1. Sets up logging and configuration
            2. Validates API key
            3. Initializes data structures for results
            4. Creates and configures three chain managers:
               - Pre-classification (method extraction, sentence analysis, summarization)
               - Classification (taxonomy-based classification)
               - Theme recognition

        Examples:
            >>> # Basic initialization with required parameters
            >>> taxonomy = Taxonomy()
            >>> abstracts = {"10.1234/example": "Sample abstract text"}
            >>> classifier = AbstractClassifier(
            ...     taxonomy=taxonomy,
            ...     doi_to_abstract_dict=abstracts,
            ...     api_key="valid-api-key"
            ... )

            >>> # Advanced initialization with custom settings
            >>> classifier = AbstractClassifier(
            ...     taxonomy=taxonomy,
            ...     doi_to_abstract_dict=abstracts,
            ...     api_key="valid-api-key",
            ...     log_to_console=True,
            ...     extra_context={"field": "computer_science"},
            ...     pre_classification_model="gpt-4",
            ...     max_classification_retries=5
            ... )
        """

        self.logger = configure_logging(
            module_name=__name__,
            log_file_name="abstract_classifier",
            log_level=DEBUG,
        )
        self.log_to_console = log_to_console
        self.logger.info("Initializing AbstractClassifier")
        self.logger.info("Performing setup")

        self.banned_categories: List[str] = []

        self.logger.info("Setting API key")
        self._run_initial_api_key_validation(api_key)
        self.api_key = api_key
        self.logger.info("API key set")

        self.logger.info("Setting taxonomy")
        self.taxonomy = taxonomy
        self.logger.info("Taxonomy set")

        self.logger.info("Setting DOI to abstract dictionary")
        self.doi_to_abstract_dict = doi_to_abstract_dict
        self.logger.info("DOI to abstract dictionary set")

        self.logger.info("Setting extra context")
        self.extra_context = extra_context
        self.logger.info("Extra context set")

        self.logger.info("Setting models")
        self._pre_classification_model = pre_classification_model
        self._classification_model = classification_model
        self._theme_model = theme_model
        self.logger.info("Models set")

        self.logger.info("Setting max classification retries")
        self.max_classification_retries = max_classification_retries
        self.logger.info(
            f"Max classification retries set to: {self.max_classification_retries}"
        )

        self.logger.info("Initialized taxonomy and abstracts")
        self.classification_results: Dict[str, Dict[str, Any]] = {
            doi: defaultdict(  # Top categories
                lambda: defaultdict(list)  # Mid categories with lists of low categories
            )
            for doi in self.doi_to_abstract_dict.keys()
        }
        self.logger.info("Initialized classification results")

        self.logger.info(
            "Initializing raw outputs list used to store raw outputs from chain layers"
        )
        self.raw_classification_outputs: List[Dict[str, Any]] = []
        self.logger.info("Initialized raw classification outputs list")

        self.logger.info(
            "Initializing raw theme outputs dictionary used to store raw outputs from theme recognition chain layers"
        )
        self.raw_theme_outputs = {doi: {} for doi in self.doi_to_abstract_dict.keys()}
        self.logger.info("Initialized raw theme outputs dictionary")

        self.logger.info("Initializing chain managers")
        self.logger.info(
            "Initializing and adding layers to pre-classification chain manager"
        )
        self.pre_classification_chain_manager: ChainManager = (
            self._initialize_pre_classification_chain_manager()
        )
        self._add_method_extraction_layer(
            self.pre_classification_chain_manager
        )._add_sentence_analysis_layer(
            self.pre_classification_chain_manager
        )._add_summary_layer(
            self.pre_classification_chain_manager
        )

        self.logger.info(
            "Pre-classification chain manager initialized and layers added"
        )

        self.logger.info(
            "Initializing and adding layers to classification chain manager"
        )
        self.classification_chain_manager: ChainManager = (
            self._initialize_classification_chain_manager()
        )
        self._add_classification_layer(self.classification_chain_manager)
        self.logger.info("Classification chain manager initialized and layers added")

        self.logger.info(
            "Initializing and adding layers to theme recognition chain manager"
        )
        self.theme_chain_manager: ChainManager = self._initialize_theme_chain_manager()
        self._add_theme_recognition_layer(self.theme_chain_manager)
        self.logger.info("Theme recognition chain manager initialized and layers added")

    def _run_initial_api_key_validation(self, api_key: str) -> None:
        """Validates the API key format and presence during initialization.

        This private method performs initial validation of the API key to ensure it exists
        and can be converted to a string type. It's called during class initialization
        before any API operations are attempted.

        Args:
            api_key: The API key to validate. Should be a non-empty string or
                a value that can be converted to a string.

        Raises:
            ValueError: If any of these conditions are met:
            - The API key is empty or None.
            - The API key cannot be converted to a string.
            - The API key conversion fails for any reason.

        Note:
            This method redacts API key values in error messages for security.

        Examples:
            >>> # Valid API key
            >>> classifier._run_initial_api_key_validation("sk-valid-key-123")  # passes

            >>> # Empty API key
            >>> try:
            ...     classifier._run_initial_api_key_validation("")
            ... except ValueError as e:
            ...     "API key is required" in str(e)
            True

            >>> # None value
            >>> try:
            ...     classifier._run_initial_api_key_validation(None)  # type: ignore
            ... except ValueError as e:
            ...     "API key is required" in str(e)
            True

            >>> # Non-string value that can be converted
            >>> classifier._run_initial_api_key_validation(123)  # passes, converts to "123"
        """
        if not api_key:
            raise ValueError(
                "API key is required"
                f"Received type: {type(api_key)}, "
                f"Value: {'<empty>' if not api_key else 'Value present but may not be a string'}"
            )

        try:
            api_key: str = cast(str, str(api_key))
        except Exception as e:
            raise ValueError(
                f"API key must be a string or be convertible to a string. "
                f"Received type: {type(api_key)}, "
                f"Value: {'<empty>' if not api_key else '<redacted>'}, "
                f"Error: {str(e)}"
            ) from e

    def _initialize_pre_classification_chain_manager(self) -> ChainManager:
        """Initializes a new ChainManager instance for pre-classification
        tasks.

        Creates and configures a ChainManager specifically for the pre-classification stage
        of the pipeline, which includes method extraction, sentence analysis, and abstract
        summarization.

        Returns:
            ChainManager: A new ChainManager instance configured with:
                - Model: self._pre_classification_model
                - Temperature: 0.0 (deterministic outputs)
                - Console logging: Based on self.log_to_console setting

        Note:
            This ChainManager is used for the initial analysis stages:
            1. Method extraction from abstracts
            2. Sentence-by-sentence analysis
            3. Abstract summarization

        Examples:
            >>> taxonomy = Taxonomy()
            >>> abstracts = {"10.1234/example": "Sample abstract"}
            >>> classifier = AbstractClassifier(taxonomy, abstracts, "api-key")
            >>> chain_manager = classifier._initialize_pre_classification_chain_manager()
            >>> isinstance(chain_manager, ChainManager)
            True
            >>> # Verify configuration
            >>> chain_manager.llm_model == classifier._pre_classification_model
            True
            >>> chain_manager.llm_temperature == 0.0
            True
        """
        return ChainManager(
            llm_model=self._pre_classification_model,
            api_key=self.api_key,
            llm_temperature=0.0,
            log_to_console=self.log_to_console,
        )

    def _initialize_classification_chain_manager(self) -> ChainManager:
        """Initializes a new ChainManager instance for taxonomy classification
        tasks.

        Creates and configures a ChainManager specifically for the classification stage
        of the pipeline, which handles the hierarchical taxonomy classification of abstracts
        at all levels (top, mid, and low).

        Returns:
            ChainManager: A new ChainManager instance configured with:
                - Model: self._classification_model
                - Temperature: 0.0 (deterministic outputs)
                - Console logging: Based on self.log_to_console setting

        Note:
            This ChainManager is used for the main classification process:
            1. Top-level category classification
            2. Mid-level category classification within each top category
            3. Low-level category classification within each mid category

            The temperature is set to 0.0 to ensure consistent classification results.

        Examples:
            >>> taxonomy = Taxonomy()
            >>> abstracts = {"10.1234/example": "Sample abstract"}
            >>> classifier = AbstractClassifier(taxonomy, abstracts, "api-key")
            >>> chain_manager = classifier._initialize_classification_chain_manager()
            >>> isinstance(chain_manager, ChainManager)
            True
            >>> # Verify configuration
            >>> chain_manager.llm_model == classifier._classification_model
            True
            >>> chain_manager.llm_temperature == 0.0
            True
        """
        return ChainManager(
            llm_model=self._classification_model,
            api_key=self.api_key,
            llm_temperature=0.0,
            log_to_console=self.log_to_console,
        )

    def _initialize_theme_chain_manager(self) -> ChainManager:
        """Initializes a new ChainManager instance for theme recognition tasks.

        Creates and configures a ChainManager specifically for the theme recognition stage
        of the pipeline, which identifies key themes and concepts from classified abstracts.

        Returns:
            ChainManager: A new ChainManager instance configured with:
                - Model: self._theme_model
                - Temperature: 0.9 (creative theme generation)
                - Console logging: Based on self.log_to_console setting

        Note:
            This ChainManager uses a higher temperature (0.9) compared to other chain managers
            because theme recognition benefits from more creative and varied outputs. The higher
            temperature allows the model to:
            1. Identify novel connections between concepts
            2. Generate diverse theme descriptions
            3. Capture nuanced relationships in the abstract

        Examples:
            >>> taxonomy = Taxonomy()
            >>> abstracts = {"10.1234/example": "Sample abstract"}
            >>> classifier = AbstractClassifier(taxonomy, abstracts, "api-key")
            >>> chain_manager = classifier._initialize_theme_chain_manager()
            >>> isinstance(chain_manager, ChainManager)
            True
            >>> # Verify configuration
            >>> chain_manager.llm_model == classifier._theme_model
            True
            >>> chain_manager.llm_temperature == 0.9  # Higher temperature for creativity
            True
        """
        return ChainManager(
            llm_model=self._theme_model,
            api_key=self.api_key,
            llm_temperature=0.9,
            log_to_console=self.log_to_console,
        )

    def _add_method_extraction_layer(self, chain_manager: ChainManager) -> Self:
        """Adds the method extraction processing layer to the chain manager.

        This layer analyzes abstracts to identify and extract research methods, techniques,
        and approaches used in the paper.

        Args:
            chain_manager (ChainManager): The chain manager to add the layer to.

        Returns:
            Self: Returns self for method chaining.

        Note:
            Configuration details:
            - System prompt: METHOD_EXTRACTION_SYSTEM_MESSAGE
            - Human prompt: HUMAN_MESSAGE_PROMPT
            - Primary parser: JSON with MethodExtractionOutput Pydantic model
            - Fallback parser: String output if JSON parsing fails
            - Output key: "method_json_output"
            - No preprocessor or postprocessor
            - No output key error ignoring

        Examples:
            >>> taxonomy = Taxonomy()
            >>> abstracts = {"10.1234/example": "Sample abstract"}
            >>> classifier = AbstractClassifier(taxonomy, abstracts, "api-key")
            >>> chain_manager = classifier._initialize_pre_classification_chain_manager()
            >>> # Add the layer and verify chain manager configuration
            >>> result = classifier._add_method_extraction_layer(chain_manager)
            >>> isinstance(result, AbstractClassifier)  # Verify method chaining
            True
            >>> # Get the added chain wrapper from the sequence
            >>> chain_sequence = chain_manager.get_chain_sequence()
            >>> chain_wrapper, output_key = chain_sequence[-1]  # Get latest added wrapper
            >>> # Verify configuration
            >>> output_key == "method_json_output"
            True
            >>> isinstance(chain_wrapper.parser, JSONParser)  # type: ignore
            True
            >>> chain_wrapper.fallback_parser is not None  # Has fallback parser
            True
            >>> chain_wrapper.preprocessor is None  # No preprocessor
            True
            >>> chain_wrapper.postprocessor is None  # No postprocessor
            True
        """
        chain_manager.add_chain_layer(
            system_prompt=METHOD_EXTRACTION_SYSTEM_MESSAGE,
            human_prompt=HUMAN_MESSAGE_PROMPT,
            parser_type="json",
            fallback_parser_type="str",
            pydantic_output_model=MethodExtractionOutput,
            output_passthrough_key_name="method_json_output",
        )
        return self

    def _add_sentence_analysis_layer(self, chain_manager: ChainManager) -> Self:
        """Adds the sentence-by-sentence analysis layer to the chain manager.

        This layer performs detailed analysis of each sentence in the abstract,
        identifying key components like objectives, methods, results, and conclusions.

        Args:
            chain_manager (ChainManager): The chain manager to add the layer to.

        Returns:
            Self: Returns self for method chaining.

        Note:
            Configuration details:
            - System prompt: ABSTRACT_SENTENCE_ANALYSIS_SYSTEM_MESSAGE
            - Human prompt: HUMAN_MESSAGE_PROMPT
            - Primary parser: JSON with AbstractSentenceAnalysis Pydantic model
            - Fallback parser: String output if JSON parsing fails
            - Output key: "sentence_analysis_output"
            - No preprocessor or postprocessor
            - No output key error ignoring

        Examples:
            >>> taxonomy = Taxonomy()
            >>> abstracts = {"10.1234/example": "Sample abstract"}
            >>> classifier = AbstractClassifier(taxonomy, abstracts, "api-key")
            >>> chain_manager = classifier._initialize_pre_classification_chain_manager()
            >>> # Add the layer and verify chain manager configuration
            >>> result = classifier._add_sentence_analysis_layer(chain_manager)
            >>> isinstance(result, AbstractClassifier)  # Verify method chaining
            True
            >>> # Get the added chain wrapper from the sequence
            >>> chain_sequence = chain_manager.get_chain_sequence()
            >>> chain_wrapper, output_key = chain_sequence[-1]  # Get latest added wrapper
            >>> # Verify configuration
            >>> output_key == "sentence_analysis_output"
            True
            >>> isinstance(chain_wrapper.parser, JSONParser)  # type: ignore
            True
            >>> chain_wrapper.fallback_parser is not None  # Has fallback parser
            True
            >>> chain_wrapper.preprocessor is None  # No preprocessor
            True
            >>> chain_wrapper.postprocessor is None  # No postprocessor
            True
        """
        chain_manager.add_chain_layer(
            system_prompt=ABSTRACT_SENTENCE_ANALYSIS_SYSTEM_MESSAGE,
            human_prompt=HUMAN_MESSAGE_PROMPT,
            parser_type="json",
            fallback_parser_type="str",
            pydantic_output_model=AbstractSentenceAnalysis,
            output_passthrough_key_name="sentence_analysis_output",
        )
        return self

    def _add_summary_layer(self, chain_manager: ChainManager) -> Self:
        """Adds the abstract summarization layer to the chain manager.

        This layer generates a concise summary of the abstract, capturing the main
        points and key findings in a structured format.

        Args:
            chain_manager (ChainManager): The chain manager to add the layer to.

        Returns:
            Self: Returns self for method chaining.

        Note:
            Configuration details:
            - System prompt: ABSTRACT_SUMMARY_SYSTEM_MESSAGE
            - Human prompt: HUMAN_MESSAGE_PROMPT
            - Primary parser: JSON with AbstractSummary Pydantic model
            - Fallback parser: String output if JSON parsing fails
            - Output key: "abstract_summary_output"
            - No preprocessor or postprocessor
            - No output key error ignoring

        Examples:
            >>> taxonomy = Taxonomy()
            >>> abstracts = {"10.1234/example": "Sample abstract"}
            >>> classifier = AbstractClassifier(taxonomy, abstracts, "api-key")
            >>> chain_manager = classifier._initialize_pre_classification_chain_manager()
            >>> # Add the layer and verify chain manager configuration
            >>> result = classifier._add_summary_layer(chain_manager)
            >>> isinstance(result, AbstractClassifier)  # Verify method chaining
            True
            >>> # Get the added chain wrapper from the sequence
            >>> chain_sequence = chain_manager.get_chain_sequence()
            >>> chain_wrapper, output_key = chain_sequence[-1]  # Get latest added wrapper
            >>> # Verify configuration
            >>> output_key == "abstract_summary_output"
            True
            >>> isinstance(chain_wrapper.parser, JSONParser)  # type: ignore
            True
            >>> chain_wrapper.fallback_parser is not None  # Has fallback parser
            True
            >>> chain_wrapper.preprocessor is None  # No preprocessor
            True
            >>> chain_wrapper.postprocessor is None  # No postprocessor
            True
        """
        chain_manager.add_chain_layer(
            system_prompt=ABSTRACT_SUMMARY_SYSTEM_MESSAGE,
            human_prompt=HUMAN_MESSAGE_PROMPT,
            parser_type="json",
            fallback_parser_type="str",
            pydantic_output_model=AbstractSummary,
            output_passthrough_key_name="abstract_summary_output",
        )
        return self

    def _add_classification_layer(self, chain_manager: ChainManager) -> Self:
        """Adds the taxonomy classification layer to the chain manager.

        This layer performs hierarchical classification of abstracts according to the
        taxonomy structure, categorizing content at top, mid, and low levels.

        Args:
            chain_manager (ChainManager): The chain manager to add the layer to.

        Returns:
            Self: Returns self for method chaining.

        Note:
            Configuration details:
            - System prompt: CLASSIFICATION_SYSTEM_MESSAGE
            - Human prompt: HUMAN_MESSAGE_PROMPT
            - Primary parser: JSON with ClassificationOutput Pydantic model
            - No fallback parser (classification must succeed)
            - Output key: "classification_output"
            - No preprocessor or postprocessor
            - No output key error ignoring

        Examples:
            >>> taxonomy = Taxonomy()
            >>> abstracts = {"10.1234/example": "Sample abstract"}
            >>> classifier = AbstractClassifier(taxonomy, abstracts, "api-key")
            >>> chain_manager = classifier._initialize_classification_chain_manager()
            >>> # Add the layer and verify chain manager configuration
            >>> result = classifier._add_classification_layer(chain_manager)
            >>> isinstance(result, AbstractClassifier)  # Verify method chaining
            True
            >>> # Get the added chain wrapper from the sequence
            >>> chain_sequence = chain_manager.get_chain_sequence()
            >>> chain_wrapper, output_key = chain_sequence[-1]  # Get latest added wrapper
            >>> # Verify configuration
            >>> output_key == "classification_output"
            True
            >>> isinstance(chain_wrapper.parser, JSONParser)  # type: ignore
            True
            >>> chain_wrapper.fallback_parser is None  # No fallback parser
            True
            >>> chain_wrapper.preprocessor is None  # No preprocessor
            True
            >>> chain_wrapper.postprocessor is None  # No postprocessor
            True
        """
        chain_manager.add_chain_layer(
            system_prompt=CLASSIFICATION_SYSTEM_MESSAGE,
            human_prompt=HUMAN_MESSAGE_PROMPT,
            parser_type="json",
            pydantic_output_model=ClassificationOutput,
            output_passthrough_key_name="classification_output",
        )
        return self

    def _add_theme_recognition_layer(self, chain_manager: ChainManager) -> Self:
        """Adds the theme recognition layer to the chain manager.

        This layer identifies and extracts key themes, concepts, and patterns from
        the abstract, providing a higher-level thematic analysis.

        Args:
            chain_manager (ChainManager): The chain manager to add the layer to.

        Returns:
            Self: Returns self for method chaining.

        Note:
            Configuration details:
            - System prompt: THEME_RECOGNITION_SYSTEM_MESSAGE
            - Human prompt: HUMAN_MESSAGE_PROMPT
            - Primary parser: JSON with ThemeAnalysis Pydantic model
            - No fallback parser
            - Output key: "theme_output"
            - No preprocessor or postprocessor
            - No output key error ignoring
            - Uses higher temperature setting for creative theme generation

        Examples:
            >>> taxonomy = Taxonomy()
            >>> abstracts = {"10.1234/example": "Sample abstract"}
            >>> classifier = AbstractClassifier(taxonomy, abstracts, "api-key")
            >>> chain_manager = classifier._initialize_theme_chain_manager()
            >>> # Add the layer and verify chain manager configuration
            >>> result = classifier._add_theme_recognition_layer(chain_manager)
            >>> isinstance(result, AbstractClassifier)  # Verify method chaining
            True
            >>> # Get the added chain wrapper from the sequence
            >>> chain_sequence = chain_manager.get_chain_sequence()
            >>> chain_wrapper, output_key = chain_sequence[-1]  # Get latest added wrapper
            >>> # Verify configuration
            >>> output_key == "theme_output"
            True
            >>> isinstance(chain_wrapper.parser, JSONParser)  # type: ignore
            True
            >>> chain_wrapper.fallback_parser is None  # No fallback parser
            True
            >>> chain_wrapper.preprocessor is None  # No preprocessor
            True
            >>> chain_wrapper.postprocessor is None  # No postprocessor
            True
        """
        chain_manager.add_chain_layer(
            system_prompt=THEME_RECOGNITION_SYSTEM_MESSAGE,
            human_prompt=HUMAN_MESSAGE_PROMPT,
            parser_type="json",
            pydantic_output_model=ThemeAnalysis,
            output_passthrough_key_name="theme_output",
        )
        return self

    def _get_classification_results_by_doi(self, doi: str) -> Dict[str, Any]:
        """Retrieves the raw classification results for a specific DOI.

        This private method provides direct access to the classification results dictionary
        for a given DOI, without theme processing. It's used internally during the
        classification pipeline, particularly before theme recognition processing.

        Args:
            doi: The DOI identifier for the abstract to retrieve results for.

        Returns:
            Dict[str, Any]: The raw classification results dictionary containing:

            - Top-level categories as keys

            - Nested dictionaries of mid-level categories

            - Lists of low-level categories


        Note:
            This method differs from the public get_classification_results_by_doi in that:

            1. It returns the raw defaultdict structure

            2. Does not include theme information

            3. Does not support different return types

            4. Used internally during classification pipeline

            5. Does not include themes (unlike the public get_classification_results_by_doi)

        Examples:
            >>> taxonomy = Taxonomy()
            >>> abstracts = {"10.1234/example": "Sample abstract"}
            >>> classifier = AbstractClassifier(taxonomy, abstracts, "api-key")
            >>> # After classification
            >>> results = classifier._get_classification_results_by_doi("10.1234/example")
            >>> isinstance(results, dict)  # Verify return type
            True
            >>> # Verify structure (no themes key)
            >>> "themes" not in results
            True
            >>> # Verify defaultdict behavior
            >>> isinstance(results.get(list(results.keys())[0]), defaultdict)  # type: ignore
            True
        """
        return self.classification_results.get(doi, {})

    def get_classification_results_by_doi(
        self, doi: str, return_type: type[dict] | type[tuple] = dict
    ) -> Union[Tuple[str, ...], Dict[str, Any]]:
        """Retrieves all categories and themes for a specific abstract via a
        DOI lookup.

        This method provides access to the complete classification results for an abstract,
        including all taxonomy levels (top, mid, low) and identified themes. Results can be
        returned either as a dictionary or as a tuple of lists.

        Args:
            doi (str): The DOI identifier for the abstract to retrieve results for.
            return_type (type[dict] | type[tuple]): The desired return type class.
                Use dict for dictionary return or tuple for tuple return.
                Defaults to dict.

        Returns:
            Union[Tuple[str, ...], Dict[str, Any]]: The classification results in the requested format:

                If return_type is dict:
                    Dictionary with keys:
                    - top_categories (List[str]): Top-level taxonomy categories
                    - mid_categories (List[str]): Mid-level taxonomy categories
                    - low_categories (List[str]): Low-level taxonomy categories
                    - themes (List[str]): Identified themes for the abstract

                If return_type is tuple:
                    Tuple of (top_categories, mid_categories, low_categories, themes)
                    where each element is a List[str]

        Note:
            - Categories at each level are returned in order of classification
            - Low-level categories are deduplicated while preserving order
            - Returns empty lists for categories/themes if DOI not found
            - Theme list will be empty if theme recognition hasn't been run

        Examples:
            >>> taxonomy = Taxonomy()
            >>> abstracts = {"10.1234/example": "Sample abstract"}
            >>> classifier = AbstractClassifier(taxonomy, abstracts, "api-key")
            >>> classifier.classify()  # Run classification first
            >>>
            >>> # Get results as dictionary
            >>> results = classifier.get_classification_results_by_doi("10.1234/example")
            >>> isinstance(results, dict)
            True
            >>> all(isinstance(results[k], list) for k in results)  # All values are lists
            True
            >>> sorted(results.keys()) == [
            ...     "low_categories",
            ...     "mid_categories",
            ...     "themes",
            ...     "top_categories"
            ... ]
            True
            >>>
            >>> # Get results as tuple
            >>> top, mid, low, themes = classifier.get_classification_results_by_doi(
            ...     "10.1234/example",
            ...     return_type=tuple
            ... )
            >>> all(isinstance(x, list) for x in (top, mid, low, themes))  # All elements are lists
            True
            >>>
            >>> # Handle non-existent DOI
            >>> results = classifier.get_classification_results_by_doi("invalid-doi")
            >>> all(len(v) == 0 for v in results.values())  # All lists are empty
            True
        """
        top_categories: List[str] = []
        mid_categories: List[str] = []
        low_categories: List[str] = []

        abstract_result: Dict[str, Any] = self.classification_results.get(doi, {})

        def extract_categories(result: Dict[str, Any], level: str) -> None:
            """Recursively extracts categories from nested classification
            results."""
            for key, value in result.items():
                if isinstance(value, dict):
                    # Handle top level categories
                    if level == "top":
                        top_categories.append(key)
                        # Recurse into mid level
                        extract_categories(value, "mid")
                elif isinstance(value, list):
                    # Handle mid and low level categories
                    if level == "mid":
                        mid_categories.append(key)
                        # Flatten and extend low categories
                        for item in value:
                            if isinstance(item, list):
                                low_categories.extend(item)
                            else:
                                low_categories.append(item)
                    elif level == "low":
                        # Flatten any nested lists
                        if isinstance(value[0], list):
                            low_categories.extend(value[0])
                        else:
                            low_categories.extend(value)

        # Start extraction from top level
        extract_categories(abstract_result, "top")

        # Remove any duplicates while preserving order
        low_categories: List[str] = list(dict.fromkeys(low_categories))

        result: Dict[str, Any] = {
            "top_categories": top_categories,
            "mid_categories": mid_categories,
            "low_categories": low_categories,
            "themes": abstract_result.get("themes", []),
        }

        return result if return_type is dict else tuple(result.values())

    def classify_abstract(
        self,
        abstract: str,
        doi: str,
        prompt_variables: Dict[str, Any],
        level: str | None = "top",
        parent_category: str | None = None,
        current_dict: Dict[str, Any] | None = None,
    ) -> None:
        """Recursively classifies an abstract through the taxonomy hierarchy.

        This method implements a depth-first traversal of the taxonomy tree, classifying
        the abstract at each level and recursively processing subcategories. It maintains
        state using a nested defaultdict structure that mirrors the taxonomy hierarchy.

        Args:
            abstract: The text of the abstract to classify.
            doi: The DOI identifier for the abstract.
            prompt_variables: Variables required for classification.
                Required from pre-classification:

                - `method_json_output`: Method extraction results.

                - `sentence_analysis_output`: Sentence analysis results.

                - `abstract_summary_output`: Abstract summary.

                Required for classification:

                - `abstract`: The abstract text.

                - `categories`: Available categories for current level.

                - `CLASSIFICATION_JSON_FORMAT`: Format specification.

                - `TAXONOMY_EXAMPLE`: Example classifications.

            level: Current taxonomy level ("top", "mid", or "low"). Defaults to "top".
            parent_category: The parent category from previous level. Defaults to `None`.
            current_dict: Current position in classification results. Defaults to `None`.

        Note:
            **Classification Process**:

            1. Pre-classification Requirements:

                - Must run method extraction.

                - Must run sentence analysis.

                - Must run abstract summarization.

                - Results must be in `prompt_variables`.

            2. Classification Flow:

                **Top Level**:

                - Classifies into top categories.

                - For each classified category:

                    - Gets its mid-level subcategories.

                    - Recursively classifies into those subcategories.

                **Mid Level**:

                - Classifies into mid categories under parent.

                - For each classified category:

                    - Gets its low-level subcategories.

                    - Recursively classifies into those subcategories.

                **Low Level**:

                - Classifies into low categories.

                - Appends results to parent mid category's list.

            3. Validation and Retry Logic:

                - Validates all classified categories against taxonomy.

                - Retries classification up to `max_classification_retries` times.

                - On final retry, bans invalid categories to force valid results.

                - Raises error if validation still fails after max retries.

        Raises:
            ValueError: If classification fails validation after max retries.
            Exception: If any other error occurs during classification.

        Examples:
            >>> taxonomy = Taxonomy()
            >>> abstracts = {"10.1234/example": "Sample abstract"}
            >>> classifier = AbstractClassifier(taxonomy, abstracts, "api-key")

            >>> # First run pre-classification to get required outputs
            >>> initial_vars = {
            ...     "abstract": abstracts["10.1234/example"],
            ...     "METHOD_JSON_FORMAT": METHOD_JSON_FORMAT,
            ...     "METHOD_EXTRACTION_CORRECT_EXAMPLE_JSON": METHOD_EXTRACTION_CORRECT_EXAMPLE_JSON,
            ...     "METHOD_EXTRACTION_INCORRECT_EXAMPLE_JSON": METHOD_EXTRACTION_INCORRECT_EXAMPLE_JSON,
            ...     "SENTENCE_ANALYSIS_JSON_EXAMPLE": SENTENCE_ANALYSIS_JSON_EXAMPLE,
            ...     "SUMMARY_JSON_STRUCTURE": SUMMARY_JSON_STRUCTURE,
            ... }
            >>> classifier.pre_classification_chain_manager.run(initial_vars)

            >>> # Get updated variables including pre-classification outputs
            >>> variables = classifier.pre_classification_chain_manager.get_chain_variables()

            >>> # Add classification-specific variables
            >>> variables.update({
            ...     "categories": classifier.taxonomy.get_top_categories(),
            ...     "CLASSIFICATION_JSON_FORMAT": CLASSIFICATION_JSON_FORMAT,
            ...     "TAXONOMY_EXAMPLE": TAXONOMY_EXAMPLE,
            ... })

            >>> # Now we can run classification
            >>> classifier.classify_abstract(
            ...     abstract=abstracts["10.1234/example"],
            ...     doi="10.1234/example",
            ...     prompt_variables=variables
            ... )
        """
        self.logger.info(f"Classifying abstract at {level} level")

        # Start at the top level of our defaultdict if not passed in
        if current_dict is None:
            current_dict = self.classification_results[doi]

        try:
            classification_output: Dict[str, Any] = (
                self.classification_chain_manager.run(
                    prompt_variables_dict=prompt_variables
                ).get("classification_output", {})
            )
            self.logger.debug(f"Raw classification output: {classification_output}")

            # Use **kwargs to unpack the dictionary into keyword arguments for the Pydantic model.
            # '**classification_output' will fill in the values for the keys in the Pydantic model
            # even if there are more keys present in the output which are not part of the pydantic model.
            # This is critical as the outputs here will have all prompt variables from the ones passed to run()
            # as well as the output of the chain layer.
            classification_output: ClassificationOutput = ClassificationOutput(
                **classification_output
            )
            self.raw_classification_outputs.append(classification_output.model_dump())

            # Extract out just the classified categories from the classification output.
            # When the level is top and mid these extracted categories will be used to recursively classify child categories
            # When the level is low these extracted categories will be used to update the current mid category's list of low categories
            classified_categories: List[str] = self.extract_classified_categories(
                classification_output
            )
            self.logger.info(
                f"Classified categories at {level} level: {classified_categories}"
            )

            # Validate categories before proceeding
            retry_count: int = 0
            while not all(
                self.is_valid_category(category, level)
                for category in classified_categories
            ):
                # Find the invalid categories
                invalid_categories: List[str] = [
                    category
                    for category in classified_categories
                    if not self.is_valid_category(category, level)
                ]
                if retry_count >= self.max_classification_retries:
                    raise ValueError(
                        f"Failed to get valid category after {self.max_classification_retries} retries. Invalid categories at {level} level. "
                        f"Invalid categories: {invalid_categories}"
                    )
                self.logger.warning(
                    f"Invalid categories at {level} level, retry {retry_count + 1} "
                    f"Invalid categories: {invalid_categories}"
                )

                # Only set banned words on the final retry.
                # This is done as words may be split into multiple tokens
                # leading to pieces of words being banned rather than the entire word.
                # This could lead to conflict with actual valid categories, and lead
                # the LLM to not classify into categories that it would otherwise.
                # This is done as a last resort to try and elicit valid categories.
                if retry_count == self.max_classification_retries - 1:
                    self.logger.warning("Final retry - attempting with token banning")
                    self.banned_categories.extend(invalid_categories)
                    self.classification_chain_manager.set_words_to_ban(
                        self.banned_categories
                    )

                # Increment retry count
                retry_count += 1

                # Retry classification at this level
                classification_output = self.classification_chain_manager.run(
                    prompt_variables_dict=prompt_variables
                ).get("classification_output", {})

                # Update the classification output with the new output
                classification_output = ClassificationOutput(**classification_output)

                # Update the classified categories with the new output
                classified_categories = self.extract_classified_categories(
                    classification_output
                )

            self.logger.info(
                f"Classified categories at {level} level: {classified_categories}"
            )

            result: Dict[str, Any] = {}

            for category in classified_categories:
                if level == "top":
                    # Get the mid categories for the current top category
                    subcategories: List[str] = self.taxonomy.get_mid_categories(
                        category
                    )

                    # Set the next level to mid so the recursive call will classify the mid categories extracted above
                    next_level: str = "mid"

                    # Move to this category's dictionary in the defaultdict
                    next_dict: Dict[str, Any] = current_dict[category]

                elif level == "mid":
                    # Get the low categories for the current mid category
                    subcategories: List[str] = self.taxonomy.get_low_categories(
                        parent_category, category
                    )

                    # Set the next level to low so the recursive call will classify the low categories extracted above
                    next_level: str = "low"

                    # Move to this category's dictionary in the defaultdict
                    next_dict: Dict[str, Any] = current_dict[category]

                elif level == "low":
                    # Append the low category to the parent (mid) category's list
                    current_dict.append(category)
                    continue

                if subcategories:
                    # Update prompt variables with new subcategories
                    prompt_variables.update(
                        {
                            "categories": subcategories,
                        }
                    )

                    # Recursively classify the subcategories
                    result[category] = self.classify_abstract(
                        abstract=abstract,
                        doi=doi,
                        prompt_variables=prompt_variables,
                        level=next_level,
                        parent_category=category,
                        current_dict=next_dict,
                    )

        except Exception as e:
            self.logger.error(
                f"Error during classification at {level} level:\n"
                f"DOI: {doi}\n"
                f"Current category: {category if 'category' in locals() else 'N/A'}\n"
                f"Parent category: {parent_category}\n"
                f"Exception: {str(e)}\n"
                f"Traceback: {traceback.format_exc()}"
            )
            raise e

    def extract_classified_categories(
        self, classification_output: ClassificationOutput
    ) -> List[str]:
        """Extracts category names from a classification output object.

        Flattens the nested structure of ClassificationOutput into a simple list of
        category names. Handles multiple classifications within the output object.

        Args:
            classification_output (ClassificationOutput): Pydantic model containing classification results.
                The model follows this structure:

                .. code-block:: python

                    {
                        "classifications": [
                            {
                                "categories": ["category1", "category2"],
                                "confidence": 0.95
                            },
                            {
                                "categories": ["category3"],
                                "confidence": 0.85
                            }
                        ]
                    }

        Returns:
            List[str]: Flattened list of all classified category names.

        Note:
            - Extracts categories from all classification entries
            - Maintains the order of categories as they appear
            - Ignores confidence scores in the output
            - Does not deduplicate categories

        Examples:
            >>> from academic_metrics.ai_data_models.ai_pydantic_models import ClassificationOutput
            >>> # Create a sample classification output
            >>> output = ClassificationOutput(classifications=[
            ...     {"categories": ["AI", "Machine Learning"], "confidence": 0.9},
            ...     {"categories": ["Deep Learning"], "confidence": 0.8}
            ... ])
            >>>
            >>> taxonomy = Taxonomy()
            >>> classifier = AbstractClassifier(taxonomy, {}, "api-key")
            >>> categories = classifier.extract_classified_categories(output)
            >>>
            >>> # Verify results
            >>> isinstance(categories, list)
            True
            >>> all(isinstance(cat, str) for cat in categories)  # All elements are strings
            True
            >>> categories == ["AI", "Machine Learning", "Deep Learning"]  # Order preserved
            True
        """
        self.logger.info("Extracting classified categories")
        categories: List[str] = [
            cat
            for classification in classification_output.classifications
            for cat in classification.categories
        ]
        self.logger.info("Extracted classified categories")
        return categories

    def is_valid_category(self, category: str, level: str) -> bool:
        """Validates if a category exists in the taxonomy at the specified
        level.

        This method delegates category validation to the taxonomy instance, checking
        whether a given category exists at the specified taxonomy level.

        Args:
            category (str): The category name to validate.
            level (str): The taxonomy level to check against.
                Must be one of: "top", "mid", or "low".

        Returns:
            bool: True if the category exists at the specified level, False otherwise.

        Note:
            This method is used during classification to:
            1. Validate classified categories before processing
            2. Trigger retry logic if invalid categories are found
            3. Support the category banning mechanism on final retries

        Examples:
            >>> from academic_metrics.utils.taxonomy_util import Taxonomy
            >>> taxonomy = Taxonomy()
            >>> abstracts = {"10.1234/example": "Sample abstract"}
            >>> classifier = AbstractClassifier(taxonomy, abstracts, "api-key")
            >>>
            >>> # Get a known valid category
            >>> top_cat = taxonomy.get_top_categories()[0]
            >>> classifier.is_valid_category(top_cat, "top")
            True
            >>>
            >>> # Test invalid category
            >>> classifier.is_valid_category("nonexistent_category", "top")
            False
            >>>
            >>> # Test category at wrong level
            >>> classifier.is_valid_category(top_cat, "low")
            False
        """
        return self.taxonomy.is_valid_category(category, level)

    def classify(self) -> Self:
        """Orchestrates the complete classification pipeline for all abstracts.

        This method manages the end-to-end processing of all abstracts present in the doi_to_abstract_dict dictionary that this AbstractClassifier instance was initialized with through.

        It does so through three stages:

        1) Pre-classification:
            - Method extraction: Identifies research methods and techniques
            - Sentence analysis: Analyzes abstract structure and components
            - Summarization: Generates structured abstract summary
        2) Classification:
            - Uses enriched data from pre-classification
            - Recursively classifies through taxonomy levels
        3) Theme Recognition:
            - Identifies key themes and concepts

        It coordinates the flow of data between stages and maintains the state of results.

        Returns:
            Self: Returns self for method chaining.

        Pipeline Stages:
            1. Pre-classification:
               - Method extraction: Identifies research methods and techniques
               - Sentence analysis: Analyzes abstract structure and components
               - Summarization: Generates structured abstract summary

            2. Classification:
               - Uses enriched data from pre-classification
               - Recursively classifies through taxonomy levels
               - Validates and retries invalid classifications

            3. Theme Recognition:
               - Processes classified abstracts
               - Identifies key themes and concepts
               - Uses higher temperature for creative analysis

        State Updates:
            - classification_results: Nested defaultdict structure with:
                .. code-block:: python

                    {
                        "doi1": {
                            "top_category1": {
                                "mid_category1": ["low1", "low2"],
                                "mid_category2": ["low3", "low4"]
                            },
                            "themes": ["theme1", "theme2"]
                        }
                    }

            - raw_classification_outputs: List of raw outputs from classification
            - raw_theme_outputs: Dictionary mapping DOIs to theme analysis results

        Note:
            - Processes abstracts sequentially
            - Requires initialized chain managers
            - Updates multiple result stores
            - Maintains logging throughout process
            - Chains data between processing stages

        Examples:
            >>> from academic_metrics.utils.taxonomy_util import Taxonomy
            >>> # Initialize with required components
            >>> taxonomy = Taxonomy()
            >>> abstracts = {
            ...     "10.1234/example": "This paper presents a novel approach..."
            ... }
            >>> classifier = AbstractClassifier(
            ...     taxonomy=taxonomy,
            ...     doi_to_abstract_dict=abstracts,
            ...     api_key="valid-api-key"
            ... )
            >>>
            >>> # Run complete pipeline
            >>> result = classifier.classify()
            >>> isinstance(result, AbstractClassifier)  # Verify method chaining
            True
            >>>
            >>> # Verify results structure
            >>> doi = "10.1234/example"
            >>> results = classifier.classification_results[doi]
            >>> isinstance(results, defaultdict)  # Nested defaultdict
            True
            >>> "themes" in results  # Theme results added
            True
            >>>
            >>> # Verify raw outputs
            >>> len(classifier.raw_classification_outputs) > 0  # Has classification outputs
            True
            >>> doi in classifier.raw_theme_outputs  # Has theme results
            True
        """
        # Track total abstracts for progress logging
        n_abstracts: int = len(self.doi_to_abstract_dict.keys())

        # Process each abstract through the complete pipeline
        for i, (doi, abstract) in enumerate(self.doi_to_abstract_dict.items()):
            # Log progress and abstract details for monitoring
            self.logger.info(f"Processing abstract {i+1} of {n_abstracts}")
            self.logger.info(f"Current DOI: {doi}")
            self.logger.info(
                f"Current abstract:\n{abstract[:10]}...{abstract[-10:]}\n\n"
            )

            #######################
            # 1. Pre-classification
            #######################

            # Initialize initial prompt variables used in the system and human prompts for the pre-classification chain layers
            initial_prompt_variables: Dict[str, Any] = {
                "abstract": abstract,
                "METHOD_JSON_FORMAT": METHOD_JSON_FORMAT,
                "METHOD_EXTRACTION_CORRECT_EXAMPLE_JSON": METHOD_EXTRACTION_CORRECT_EXAMPLE_JSON,
                "METHOD_EXTRACTION_INCORRECT_EXAMPLE_JSON": METHOD_EXTRACTION_INCORRECT_EXAMPLE_JSON,
                "SENTENCE_ANALYSIS_JSON_EXAMPLE": SENTENCE_ANALYSIS_JSON_EXAMPLE,
                "SUMMARY_JSON_STRUCTURE": SUMMARY_JSON_STRUCTURE,
                "extra_context": self.extra_context,
            }

            # Execute pre-classification chain (method extraction -> sentence analysis -> summarization)
            self.pre_classification_chain_manager.run(
                prompt_variables_dict=initial_prompt_variables
            )

            # Call this (pre_classification_chain_manager) ChainManager instance's get_chain_variables() method to get the current
            # chain variables which includes all initial_prompt_variables and the outputs of the
            # The new items inserted have a key which matches the layers output_passthrough_key_name value.
            prompt_variables: Dict[str, Any] = (
                self.pre_classification_chain_manager.get_chain_variables()
            )
            method_extraction_output: Dict[str, Any] = prompt_variables.get(
                "method_json_output", {}
            )
            self.logger.debug(f"Method extraction output: {method_extraction_output}")
            sentence_analysis_output: Dict[str, Any] = prompt_variables.get(
                "sentence_analysis_output", {}
            )
            self.logger.debug(f"Sentence analysis output: {sentence_analysis_output}")
            summary_output: Dict[str, Any] = prompt_variables.get(
                "abstract_summary_output", {}
            )
            self.logger.debug(f"Summary output: {summary_output}")

            ######################
            # 2. Classification
            ######################

            # Update the prompt variables by adding classification-specific variables.
            # Start with top-level categories - recursive classification will handle lower levels.
            prompt_variables.update(
                {
                    "categories": self.taxonomy.get_top_categories(),
                    "CLASSIFICATION_JSON_FORMAT": CLASSIFICATION_JSON_FORMAT,
                    "TAXONOMY_EXAMPLE": TAXONOMY_EXAMPLE,
                }
            )

            # Execute recursive classification through taxonomy levels
            self.classify_abstract(
                abstract=abstract,
                doi=doi,
                prompt_variables=prompt_variables,
            )

            ######################
            # 3. Theme Recognition
            ######################

            # Get updated variables after classification.
            # Details:
            #   Once classify_abstract returns it will have classified the abstract into top categories
            #   then recursively classified mid and low level categories within each classified top category
            #   so now this abstract has been classified into all relevant categories and subcategories within the taxonomy.
            #   Given this, we can now process the themes for this abstract.
            #   Like before fetch this ChainManager (classification_chain_manager this time) instance's chain variables and update them:
            prompt_variables: Dict[str, Any] = (
                self.classification_chain_manager.get_chain_variables()
            )

            # Add in the theme recognition specific variables
            # The only one not already present in prompt_variables which is present as a placeholder
            # in the theme_recognition_system_prompt is THEME_RECOGNITION_JSON_FORMAT, so we add that in.
            # Then update the categories key with the categories from the classification results.
            prompt_variables.update(
                {
                    "THEME_RECOGNITION_JSON_FORMAT": THEME_RECOGNITION_JSON_FORMAT,
                    "categories": self._get_classification_results_by_doi(doi),
                }
            )

            # Execute theme recognition on the current abstract.
            # Details:
            #   Here we actually store the result as we want to want to store this raw output into the raw theme outputs dictionary
            #   We don't need to pull out prompt_variables again as we can just extract the themes directly out the theme_results
            #   Remember, before we had to pull out the prompt_variables as we needed all variables to propagate through to the
            #   future chains which weren't the same ChainManager instance.
            theme_results: Dict[str, Any] = self.theme_chain_manager.run(
                prompt_variables_dict=prompt_variables
            ).get("theme_output", {})

            theme_results = ThemeAnalysis(**theme_results)

            # Store raw theme results
            self.raw_theme_outputs[doi] = theme_results.model_dump()

            # Update final classification results with themes
            # Details:
            #   Done in an if statement to avoid killing the live service if this happens, though it shouldn't,
            #   or at least a more explicit and detailed error should be thrown much earlier.
            #   Due to the context here not much detail is known, so throwing an error isn't particularly helpful.
            if doi in self.classification_results:
                self.classification_results[doi]["themes"] = theme_results.themes
            else:
                # Log error if DOI missing from results (as mentioned before, this shouldn't happen in normal operation, but just in case)
                self.logger.error(
                    f"DOI not found in classification results: {doi}, class results: {self.classification_results}"
                )

        return self

    def _make_dirs_helper(self, output_path: str) -> None:
        """Creates necessary directories for an output file path.

        This private helper method ensures that all directories in the path exist,
        creating them if necessary. Used by save methods before writing files.

        Args:
            output_path (str): The full path where a file will be saved.
                Can be either absolute or relative path.

        Note:
            - Creates directories recursively
            - Uses exist_ok=True to handle existing directories
            - Creates parent directories only (not the file itself)

        Examples:
            >>> taxonomy = Taxonomy()
            >>> classifier = AbstractClassifier(taxonomy, {}, "api-key")
            >>> # Create nested directory structure
            >>> classifier._make_dirs_helper("outputs/results/data.json")
            >>> import os
            >>> os.path.exists("outputs/results")  # Directories were created
            True
            >>> # Handle existing directories
            >>> classifier._make_dirs_helper("outputs/results/data.json")  # No error
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    def save_classification_results(self, output_path: str) -> Self:
        """Saves processed classification results to a JSON file.

        Writes the complete classification results dictionary to a JSON file,
        creating any necessary directories in the process. The output includes
        all categories and themes for all processed abstracts.

        Args:
            output_path (str): Path where the JSON file should be saved.
                Can be absolute or relative path.

        Returns:
            Self: Returns self for method chaining.

        Note:
            Output Format:
                .. code-block:: python

                    {
                        "doi1": {
                            "top_category1": {
                                "mid_category1": ["low1", "low2"],
                                "mid_category2": ["low3", "low4"]
                            },
                            "themes": ["theme1", "theme2"]
                        }
                    }

        Examples:
            >>> from academic_metrics.utils.taxonomy_util import Taxonomy
            >>> # Basic usage
            >>> taxonomy = Taxonomy()
            >>> classifier = AbstractClassifier(taxonomy, {}, "api-key")
            >>> classifier.save_classification_results("results/data.json")
            >>> import os
            >>> os.path.exists("results/data.json")  # File was created
            True
            >>> 
            >>> # Method chaining
            >>> classifier.classify()\\
            ...     .save_classification_results("results/data1.json")\\
            ...     .save_classification_results("results/data2.json")  # Chain multiple saves
            >>> 
            >>> # Verify file contents
            >>> import json
            >>> with open("results/data.json") as f:
            ...     saved_data = json.load(f)
            >>> saved_data == classifier.classification_results  # Data matches
            True
        """
        self.logger.info("Saving classification results")
        self._make_dirs_helper(output_path)
        with open(output_path, "w") as f:
            json.dump(self.classification_results, f, indent=4)
        return self

    def get_classification_results_dict(self) -> Dict[str, Dict[str, Any]]:
        """Retrieves processed classification results for all processed
        abstracts.

        Provides direct access to the complete classification results dictionary,
        containing all categories and themes for every processed abstract.

        Returns:
            Dict[str, Dict[str, Any]]: A dictionary where:
                - Keys are DOI strings
                - Values are nested dictionaries containing:
                    .. code-block:: python

                        {
                            "top_category1": {
                                "mid_category1": ["low1", "low2"],
                                "mid_category2": ["low3", "low4"]
                            },
                            "themes": ["theme1", "theme2"]
                        }

        Note:
            - Returns the raw defaultdict structure
            - Includes theme information if theme recognition was run
            - Structure matches the save_classification_results output format

        Examples:
            >>> taxonomy = Taxonomy()
            >>> abstracts = {"10.1234/example": "Sample abstract"}
            >>> classifier = AbstractClassifier(taxonomy, abstracts, "api-key")
            >>> classifier.classify()  # Process abstracts first
            >>>
            >>> # Get results
            >>> results = classifier.get_classification_results_dict()
            >>> isinstance(results, dict)  # Verify return type
            True
            >>> # Verify structure for a DOI
            >>> doi_results = results["10.1234/example"]
            >>> isinstance(doi_results, defaultdict)  # Nested defaultdict
            True
            >>> "themes" in doi_results  # Has themes
            True
        """
        self.logger.info("Getting classification results")
        return self.classification_results

    def get_raw_classification_outputs(self) -> List[Dict[str, Any]]:
        """Retrieves raw classification outputs from all processed abstracts.

        Provides access to the complete, unprocessed outputs from the classification
        chain, including all prompt variables and intermediate results.

        Returns:
            List[Dict[str, Any]]: List of raw classification outputs, where each output
            contains:

            - `"classifications"`: List of classifications with categories and confidence scores.

            - `"abstract"`: The original abstract text.

            - `"method_json_output"`: Output from method extraction.

            - `"sentence_analysis_output"`: Output from sentence analysis.

            - `"abstract_summary_output"`: Output from abstract summarization.

            - Other chain variables and outputs.

        Note:
            - Contains all chain variables and outputs.
            - Includes pre-classification results.
            - Useful for debugging and analysis.
            - May contain large amounts of data.

        Examples:
            >>> taxonomy = Taxonomy()
            >>> abstracts = {"10.1234/example": "Sample abstract"}
            >>> classifier = AbstractClassifier(taxonomy, abstracts, "api-key")
            >>> classifier.classify()  # Process abstracts first

            >>> # Get raw outputs
            >>> outputs = classifier.get_raw_classification_outputs()
            >>> isinstance(outputs, list)  # Verify return type
            True
            >>> # Verify structure of first output
            >>> first_output = outputs[0]
            >>> "classifications" in first_output  # Has classifications
            True
            >>> isinstance(first_output["classifications"], list)  # List of classifications
            True
        """
        self.logger.info("Getting raw classification outputs")
        return self.raw_classification_outputs

    def get_raw_theme_results(self) -> Dict[str, Dict[str, Any]]:
        """Retrieves raw theme analysis results for all processed abstracts.

        Provides access to the complete, unprocessed outputs from the theme recognition
        chain for each abstract.

        Returns:
            Dict[str, Dict[str, Any]]: Dictionary where:
                - Keys are DOI strings
                - Values are raw theme analysis results with structure:
                    .. code-block:: python

                        {
                            "themes": ["theme1", "theme2"],
                            "confidence_scores": {
                                "theme1": 0.95,
                                "theme2": 0.85
                            },
                            "analysis": "Theme analysis text...",
                            # Other theme recognition outputs
                        }

        Note:
            - Contains complete theme recognition outputs
            - Includes confidence scores and analysis text
            - Available after theme recognition stage
            - Empty dictionaries for unprocessed DOIs

        Examples:
            >>> taxonomy = Taxonomy()
            >>> abstracts = {"10.1234/example": "Sample abstract"}
            >>> classifier = AbstractClassifier(taxonomy, abstracts, "api-key")
            >>> classifier.classify()  # Process abstracts first
            >>>
            >>> # Get theme results
            >>> themes = classifier.get_raw_theme_results()
            >>> isinstance(themes, dict)  # Verify return type
            True
            >>> # Verify structure for a DOI
            >>> doi_themes = themes["10.1234/example"]
            >>> "themes" in doi_themes  # Has themes list
            True
            >>> isinstance(doi_themes["themes"], list)  # Themes are in a list
            True
        """
        self.logger.info("Getting raw theme results")
        return self.raw_theme_outputs

    def save_raw_classification_results(self, output_path: str) -> Self:
        """Saves raw classification outputs to a JSON file.

        Writes the complete, unprocessed outputs from the classification chain to a JSON file,
        creating any necessary directories in the process. Includes all prompt variables and
        intermediate results.

        Args:
            output_path (str): Path where the JSON file should be saved.
                Can be absolute or relative path.

        Returns:
            Self: Returns self for method chaining.

        Note:
            Output Format:
                .. code-block:: python

                    [
                        {
                            "classifications": [
                                {
                                    "categories": ["category1", "category2"],
                                    "confidence": 0.95
                                }
                            ],
                            "abstract": "original abstract text",
                            "method_json_output": {...},
                            "sentence_analysis_output": {...},
                            "abstract_summary_output": {...},
                            # Other chain variables and outputs
                        },
                        # Additional classification outputs...
                    ]

        Examples:
            >>> from academic_metrics.utils.taxonomy_util import Taxonomy
            >>> # Basic usage
            >>> taxonomy = Taxonomy()
            >>> abstracts = {"10.1234/example": "Sample abstract"}
            >>> classifier = AbstractClassifier(taxonomy, abstracts, "api-key")
            >>> classifier.classify()  # Process abstracts first
            >>> classifier.save_raw_classification_results("debug/raw_outputs.json")
            >>> import os
            >>> os.path.exists("debug/raw_outputs.json")  # File was created
            True
            >>> 
            >>> # Method chaining
            >>> classifier.classify()\\
            ...     .save_raw_classification_results("debug/raw1.json")\\
            ...     .save_raw_classification_results("debug/raw2.json")
            >>> 
            >>> # Verify file contents
            >>> import json
            >>> with open("debug/raw_outputs.json") as f:
            ...     saved_data = json.load(f)
            >>> saved_data == classifier.raw_classification_outputs  # Data matches
            True
        """
        self.logger.info("Saving raw classification results")
        self._make_dirs_helper(output_path)
        with open(output_path, "w") as f:
            json.dump(self.raw_classification_outputs, f, indent=4)
        return self

    def save_raw_theme_results(self, output_path: str) -> Self:
        """Saves raw theme analysis results to a JSON file.

        Writes the complete, unprocessed outputs from the theme recognition chain to a JSON file,
        creating any necessary directories in the process. Includes theme analysis results for
        each processed abstract.

        Args:
            output_path (str): Path where the JSON file should be saved.
                Can be absolute or relative path.

        Returns:
            Self: Returns self for method chaining.

        Note:
            Output Format:
                .. code-block:: python

                    {
                        "10.1234/example": {
                            "themes": ["theme1", "theme2"],
                            "confidence_scores": {
                                "theme1": 0.95,
                                "theme2": 0.85
                            },
                            "analysis": "Theme analysis text...",
                            # Other theme recognition outputs
                        },
                        # Additional DOIs and their theme results...
                    }

        Examples:
            >>> from academic_metrics.utils.taxonomy_util import Taxonomy
            >>> # Basic usage
            >>> taxonomy = Taxonomy()
            >>> abstracts = {"10.1234/example": "Sample abstract"}
            >>> classifier = AbstractClassifier(taxonomy, abstracts, "api-key")
            >>> classifier.classify()  # Process abstracts first
            >>> classifier.save_raw_theme_results("debug/raw_themes.json")
            >>> import os
            >>> os.path.exists("debug/raw_themes.json")  # File was created
            True
            >>> 
            >>> # Method chaining
            >>> classifier.classify()\\
            ...     .save_raw_theme_results("debug/themes1.json")\\
            ...     .save_raw_theme_results("debug/themes2.json")
            >>> 
            >>> # Verify file contents
            >>> import json
            >>> with open("debug/raw_themes.json") as f:
            ...     saved_data = json.load(f)
            >>> saved_data == classifier.raw_theme_outputs  # Data matches
            True
        """
        self.logger.info("Saving raw theme results")
        self._make_dirs_helper(output_path)
        with open(output_path, "w") as f:
            json.dump(self.raw_theme_outputs, f, indent=4)
        return self


if __name__ == "__main__":
    """Simple demonstration of AbstractClassifier functionality.

    This script shows basic usage of the AbstractClassifier class by:
    1. Loading environment variables for API key
    2. Creating a sample abstract
    3. Initializing and running the classifier
    4. Saving results to files
    """
    from academic_metrics.utils.taxonomy_util import Taxonomy
    from dotenv import load_dotenv
    import os

    # Load environment variables
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")

    # Create sample data
    sample_abstract = {
        "10.1234/example": (
            "This paper presents a novel machine learning approach for natural "
            "language processing. We introduce a new neural network architecture "
            "that combines transformer models with reinforcement learning. Our "
            "results show significant improvements in language understanding tasks."
        )
    }

    extra_context = {
        "keywords": [
            "machine learning",
            "natural language processing",
            "neural networks",
            "reinforcement learning",
        ]
    }

    # Initialize classifier
    taxonomy = Taxonomy()
    classifier = AbstractClassifier(
        taxonomy=taxonomy,
        doi_to_abstract_dict=sample_abstract,
        api_key=api_key,
        extra_context=extra_context,
    )

    # Run classification and save results
    try:
        classifier.classify().save_classification_results(
            "outputs/classification_results.json"
        ).save_raw_theme_results(
            "outputs/theme_results.json"
        ).save_raw_classification_results(
            "outputs/raw_classification_outputs.json"
        )
        print("Classification completed successfully. Results saved to outputs/")
    except Exception as e:
        print(f"Error during classification: {str(e)}")
