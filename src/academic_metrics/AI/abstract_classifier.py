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
from academic_metrics.ai_prompts import (
    # Method prompts
    METHOD_EXTRACTION_CORRECT_EXAMPLE_JSON,
    METHOD_EXTRACTION_INCORRECT_EXAMPLE_JSON,
    METHOD_EXTRACTION_SYSTEM_MESSAGE,
    METHOD_JSON_FORMAT,
    # Sentence analysis prompts
    ABSTRACT_SENTENCE_ANALYSIS_SYSTEM_MESSAGE,
    SENTENCE_ANALYSIS_JSON_EXAMPLE,
    # Summary prompts
    ABSTRACT_SUMMARY_SYSTEM_MESSAGE,
    SUMMARY_JSON_STRUCTURE,
    # Classification prompts
    CLASSIFICATION_JSON_FORMAT,
    CLASSIFICATION_SYSTEM_MESSAGE,
    TAXONOMY_EXAMPLE,
    # Theme prompts
    THEME_RECOGNITION_JSON_FORMAT,
    THEME_RECOGNITION_SYSTEM_MESSAGE,
    # Human prompt
    HUMAN_MESSAGE_PROMPT,
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
    """A class for processing research paper abstracts through AI-powered analysis and classification.

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

    Args:
        taxonomy (Taxonomy): Taxonomy instance containing the classification hierarchy
        doi_to_abstract_dict (Dict[str, str]): Mapping of DOIs to abstract texts
        api_key (str): API key for LLM access
        log_to_console (bool, optional): Whether to log output to console. Defaults to True
        extra_context (Dict[str, Any], optional): Additional context for classification. Defaults to None
        pre_classification_model (str, optional): Model name for pre-classification tasks. Defaults to "gpt-4o-mini"
        classification_model (str, optional): Model name for classification tasks. Defaults to "gpt-4o-mini"
        theme_model (str, optional): Model name for theme recognition tasks. Defaults to "gpt-4o-mini"
        max_classification_retries (int, optional): Maximum retries for failed classifications. Defaults to 3

    Attributes:
        classification_results (Dict[str, Dict]): Processed results by DOI, containing categories and themes
        raw_classification_outputs (List[Dict]): Raw outputs from the classification chain
        raw_theme_outputs (Dict[str, Dict]): Raw theme analysis results by DOI

    Methods:
        classify(): Process all abstracts through the complete pipeline
        get_classification_results_by_doi(doi, return_type): Get results for a specific DOI
        get_raw_classification_outputs(): Get all raw classification outputs
        get_raw_theme_results(): Get all raw theme analysis results
        save_classification_results(output_path): Save processed results to JSON
        save_raw_classification_results(output_path): Save raw classification outputs
        save_raw_theme_results(output_path): Save raw theme results

    Raises:
        ValueError: If required attributes are missing or invalid
        TypeError: If api_key cannot be converted to string
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
            taxonomy (Taxonomy): Taxonomy instance containing the hierarchical category structure.
                Type: :class:`academic_metrics.utils.taxonomy_util.Taxonomy`
            doi_to_abstract_dict (Dict[str, str]): Dictionary mapping DOIs to their abstract texts.
            api_key (str): API key for accessing the language model service.
            log_to_console (bool | None): Whether to output logs to console.
                Type: bool | None
                Defaults to LOG_TO_CONSOLE config value.
            extra_context (Dict[str, Any] | None): Additional context for classification.
                Type: Dict[str, Any] | None
                Defaults to None.
            pre_classification_model (str | None): Model name for pre-classification tasks.
                Type: str | None
                Defaults to "gpt-4o-mini".
            classification_model (str | None): Model name for classification tasks.
                Type: str | None
                Defaults to "gpt-4o-mini".
            theme_model (str | None): Model name for theme recognition tasks.
                Type: str | None
                Defaults to "gpt-4o-mini".
            max_classification_retries (int | None): Maximum attempts for failed classifications.
                Type: int | None
                Defaults to 3.

        Raises:
            ValueError: If api_key is empty or invalid.
            TypeError: If api_key cannot be converted to string.
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
        self.logger.debug(
            f"pre_classification_model (before setting): {pre_classification_model}"
        )
        self._pre_classification_model = pre_classification_model
        self.logger.debug(
            f"_pre_classification_model (after setting): {self._pre_classification_model}"
        )
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

        Performs initial validation of the API key to ensure it exists and can be
        converted to a string type. Called during class initialization before any
        API operations are attempted.

        Args:
            api_key (str): The API key to validate. Should be a non-empty string or a value that can be converted to a string.
                Type: str

        Raises:
            ValueError: If the API key is empty, None, cannot be converted to a string,
                or if the conversion fails for any reason.

        Returns:
            None
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
        """Initializes a new ChainManager instance for pre-classification tasks.

        Creates and configures a ChainManager specifically for the pre-classification stage
        of the pipeline, which includes method extraction, sentence analysis, and abstract
        summarization.

        Returns:
            ChainManager: A new ChainManager instance configured with:
                Type: :class:`academic_metrics.ChainBuilder.ChainBuilder.ChainManager`
                - Model: self._pre_classification_model
                - Temperature: 0.0 (deterministic outputs)
                - Console logging: Based on self.log_to_console setting
        """
        self.logger.debug(
            f"pre_classification_model type: {type(self._pre_classification_model)}"
        )
        self.logger.debug(
            f"pre_classification_model value: {self._pre_classification_model}"
        )
        return ChainManager(
            llm_model=self._pre_classification_model,
            api_key=self.api_key,
            llm_temperature=0.0,
            log_to_console=self.log_to_console,
        )

    def _initialize_classification_chain_manager(self) -> ChainManager:
        """Initializes a new ChainManager instance for taxonomy classification tasks.

        Creates and configures a ChainManager specifically for the classification stage
        of the pipeline, which handles the hierarchical taxonomy classification of abstracts
        at all levels (top, mid, and low).

        Returns:
            ChainManager: A new ChainManager instance configured with:
                Type: :class:`academic_metrics.ChainBuilder.ChainBuilder.ChainManager`
                - Model: self._classification_model
                - Temperature: 0.0 (deterministic outputs)
                - Console logging: Based on self.log_to_console setting
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

        Args:
            None

        Returns:
            ChainManager: A new ChainManager instance configured with:
                Type: :class:`academic_metrics.ChainBuilder.ChainBuilder.ChainManager`
                - Model: self._theme_model
                - Temperature: 0.9 (creative theme generation)
                - Console logging: Based on self.log_to_console setting
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
                Type: :class:`academic_metrics.ChainBuilder.ChainBuilder.ChainManager`

        Returns:
            Self: Returns self for method chaining.
                Type: :class:`academic_metrics.AI.AbstractClassifier.AbstractClassifier`

        Notes:
            - System prompt: METHOD_EXTRACTION_SYSTEM_MESSAGE
            - Human prompt: HUMAN_MESSAGE_PROMPT
            - Primary parser: JSON with MethodExtractionOutput Pydantic model
            - Fallback parser: String output if JSON parsing fails
            - Output key: "method_json_output"
            - No preprocessor or postprocessor
            - No output key error ignoring
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
                Type: :class:`academic_metrics.ChainBuilder.ChainBuilder.ChainManager`

        Returns:
            Self: Returns self for method chaining.
                Type: :class:`academic_metrics.AI.AbstractClassifier.AbstractClassifier`

        Notes:
            - System prompt: ABSTRACT_SENTENCE_ANALYSIS_SYSTEM_MESSAGE
            - Human prompt: HUMAN_MESSAGE_PROMPT
            - Primary parser: JSON with AbstractSentenceAnalysis Pydantic model
            - Fallback parser: String output if JSON parsing fails
            - Output key: "sentence_analysis_output"
            - No preprocessor or postprocessor
            - No output key error ignoring
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
                Type: :class:`academic_metrics.ChainBuilder.ChainBuilder.ChainManager`

        Returns:
            Self: Returns self for method chaining.
                Type: :class:`academic_metrics.AI.AbstractClassifier.AbstractClassifier`

        Notes:
            - System prompt: ABSTRACT_SUMMARY_SYSTEM_MESSAGE
            - Human prompt: HUMAN_MESSAGE_PROMPT
            - Primary parser: JSON with AbstractSummary Pydantic model
            - Fallback parser: String output if JSON parsing fails
            - Output key: "abstract_summary_output"
            - No preprocessor or postprocessor
            - No output key error ignoring
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
                Type: :class:`academic_metrics.ChainBuilder.ChainBuilder.ChainManager`

        Returns:
            Self: Returns self for method chaining.
                Type: :class:`academic_metrics.AI.AbstractClassifier.AbstractClassifier`

        Notes:
            - System prompt: CLASSIFICATION_SYSTEM_MESSAGE
            - Human prompt: HUMAN_MESSAGE_PROMPT
            - Primary parser: JSON with ClassificationOutput Pydantic model
            - No fallback parser (classification must succeed)
            - Output key: "classification_output"
            - No preprocessor or postprocessor
            - No output key error ignoring
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
                Type: :class:`academic_metrics.ChainBuilder.ChainBuilder.ChainManager`

        Returns:
            Self: Returns self for method chaining.
                Type: :class:`academic_metrics.AI.AbstractClassifier.AbstractClassifier`

        Notes:
            - System prompt: THEME_RECOGNITION_SYSTEM_MESSAGE
            - Human prompt: HUMAN_MESSAGE_PROMPT
            - Primary parser: JSON with ThemeAnalysis Pydantic model
            - No fallback parser
            - Output key: "theme_output"
            - No preprocessor or postprocessor
            - No output key error ignoring
            - Uses higher temperature setting for creative theme generation
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
            doi (str): The DOI identifier for the abstract to retrieve results for.
                Type: str

        Returns:
            Dict[str, Any]: The raw classification results dictionary containing:
                Type: Dict[str, Any]
                - Top-level categories as keys
                - Nested dictionaries of mid-level categories
                - Lists of low-level categories

        Notes:
            - Returns the raw defaultdict structure
            - Does not include theme information
            - Does not support different return types
            - Used internally during classification pipeline
            - Does not include themes (unlike the public get_classification_results_by_doi)
        """
        return self.classification_results.get(doi, {})

    def get_classification_results_by_doi(
        self, doi: str, return_type: type[dict] | type[tuple] = dict
    ) -> Union[Tuple[str, ...], Dict[str, Any]]:
        """Retrieves all categories and themes for a specific abstract via a DOI lookup.

        This method provides access to the complete classification results for an abstract,
        including all taxonomy levels (top, mid, low) and identified themes. Results can be
        returned either as a dictionary or as a tuple of lists.

        Args:
            doi (str): The DOI identifier for the abstract to retrieve results for.
                Type: str
            return_type (type[dict] | type[tuple]): The desired return type class.
                Type: type[dict] | type[tuple]
                Use dict for dictionary return or tuple for tuple return.
                Defaults to dict.

        Returns:
            Union[Tuple[str, ...], Dict[str, Any]]: The classification results in the requested format:
                Type: Union[Tuple[str, ...], Dict[str, Any]]

                If dict return type:
                    - top_categories (List[str]): Top-level taxonomy categories
                    - mid_categories (List[str]): Mid-level taxonomy categories
                    - low_categories (List[str]): Low-level taxonomy categories
                    - themes (List[str]): Identified themes for the abstract

                If tuple return type:
                    Tuple of (top_categories, mid_categories, low_categories, themes)
                    where each element is a List[str]

        Notes:
            - Categories at each level are returned in order of classification
            - Low-level categories are deduplicated while preserving order
            - Returns empty lists for categories/themes if DOI not found
            - Theme list will be empty if theme recognition hasn't been run
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
            abstract (str): The text of the abstract to classify.
                Type: str
            doi (str): The DOI identifier for the abstract.
                Type: str
            prompt_variables (Dict[str, Any]): Variables required for classification.
                Type: Dict[str, Any]
                Pre-classification requirements:
                - method_json_output: Method extraction results
                - sentence_analysis_output: Sentence analysis results
                - abstract_summary_output: Abstract summary
                Classification requirements:
                - abstract: The abstract text
                - categories: Available categories for current level
                - CLASSIFICATION_JSON_FORMAT: Format specification
                - TAXONOMY_EXAMPLE: Example classifications
            level (str | None): Current taxonomy level ("top", "mid", or "low").
                Type: str | None
                Defaults to "top".
            parent_category (str | None): The parent category from previous level.
                Type: str | None
                Defaults to None.
            current_dict (Dict[str, Any] | None): Current position in classification results.
                Type: Dict[str, Any] | None
                Defaults to None.

        Returns:
            None

        Raises:
            ValueError: If classification fails validation after max retries.
            Exception: If any other error occurs during classification.

        Notes:
            - Pre-classification must run method extraction, sentence analysis, and summarization
            - Top level classification processes into top categories then recursively into subcategories
            - Mid level classification processes into mid categories under parent then into low categories
            - Low level classification appends results to parent mid category's list
            - Validates all classified categories against taxonomy
            - Retries classification up to max_classification_retries times
            - On final retry, bans invalid categories to force valid results
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
                Type: :class:`academic_metrics.AI.models.ClassificationOutput`
                Structure:
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
                Type: List[str]

        Notes:
            - Extracts categories from all classification entries
            - Maintains the order of categories as they appear
            - Ignores confidence scores in the output
            - Does not deduplicate categories
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
        """Validates if a category exists in the taxonomy at the specified level.

        This method delegates category validation to the taxonomy instance, checking
        whether a given category exists at the specified taxonomy level.

        Args:
            category (str): The category name to validate.
                Type: str
            level (str): The taxonomy level to check against.
                Type: str
                Must be one of: "top", "mid", or "low".

        Returns:
            bool: True if the category exists at the specified level, False otherwise.
                Type: bool

        Notes:
            - Used to validate classified categories before processing
            - Triggers retry logic if invalid categories are found
            - Supports the category banning mechanism on final retries
        """
        return self.taxonomy.is_valid_category(category, level)

    def classify(self) -> Self:
        """Orchestrates the complete classification pipeline for all abstracts.

        This method manages the end-to-end processing of all abstracts present in the
        doi_to_abstract_dict dictionary through three stages: pre-classification,
        classification, and theme recognition.

        Args:
            None

        Returns:
            Self: Returns self for method chaining.
                Type: :class:`academic_metrics.AI.AbstractClassifier.AbstractClassifier`

        Notes:
            Pipeline Stages:
            - Pre-classification:
                - Method extraction: Identifies research methods and techniques
                - Sentence analysis: Analyzes abstract structure and components
                - Summarization: Generates structured abstract summary

            - Classification:
                - Uses enriched data from pre-classification
                - Recursively classifies through taxonomy levels
                - Validates and retries invalid classifications

            - Theme Recognition:
                - Processes classified abstracts
                - Identifies key themes and concepts
                - Uses higher temperature for creative analysis

            State Updates:
            - classification_results: Nested defaultdict structure:
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

            Processing Details:
            - Processes abstracts sequentially
            - Requires initialized chain managers
            - Updates multiple result stores
            - Maintains logging throughout process
            - Chains data between processing stages
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
                Type: str
                Can be either absolute or relative path.

        Notes:
            - Creates directories recursively
            - Uses exist_ok=True to handle existing directories
            - Creates parent directories only (not the file itself)
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    def save_classification_results(self, output_path: str) -> Self:
        """Saves processed classification results to a JSON file.

        Writes the complete classification results dictionary to a JSON file,
        creating any necessary directories in the process. The output includes
        all categories and themes for all processed abstracts.

        Args:
            output_path (str): Path where the JSON file should be saved.
                Type: str
                Can be absolute or relative path.

        Returns:
            Self: Returns self for method chaining.
                Type: :class:`academic_metrics.AI.AbstractClassifier.AbstractClassifier`

        Notes:
            Output Format:
            {
                "doi1": {
                    "top_category1": {
                        "mid_category1": ["low1", "low2"],
                        "mid_category2": ["low3", "low4"]
                    },
                    "themes": ["theme1", "theme2"]
                }
            }
        """
        self.logger.info("Saving classification results")
        self._make_dirs_helper(output_path)
        with open(output_path, "w") as f:
            json.dump(self.classification_results, f, indent=4)
        return self

    def get_classification_results_dict(self) -> Dict[str, Dict[str, Any]]:
        """Retrieves processed classification results for all processed abstracts.

        Provides direct access to the complete classification results dictionary,
        containing all categories and themes for every processed abstract.

        Returns:
            Dict[str, Dict[str, Any]]: A dictionary where:
                Type: Dict[str, Dict[str, Any]]
                - Keys are DOI strings
                - Values are nested dictionaries containing:
                {
                    "top_category1": {
                        "mid_category1": ["low1", "low2"],
                        "mid_category2": ["low3", "low4"]
                    },
                    "themes": ["theme1", "theme2"]
                }

        Notes:
            - Returns the raw defaultdict structure
            - Includes theme information if theme recognition was run
            - Structure matches the save_classification_results output format
        """
        self.logger.info("Getting classification results")
        return self.classification_results

    def get_raw_classification_outputs(self) -> List[Dict[str, Any]]:
        """Retrieves raw classification outputs from all processed abstracts.

        Provides access to the complete, unprocessed outputs from the classification
        chain, including all prompt variables and intermediate results.

        Returns:
            List[Dict[str, Any]]: List of raw classification outputs, where each output contains:
                Type: List[Dict[str, Any]]
                - classifications: List of classifications with categories and confidence scores
                - abstract: The original abstract text
                - method_json_output: Output from method extraction
                - sentence_analysis_output: Output from sentence analysis
                - abstract_summary_output: Output from abstract summarization
                - Other chain variables and outputs

        Notes:
            - Contains all chain variables and outputs
            - Includes pre-classification results
            - Useful for debugging and analysis
            - May contain large amounts of data
        """
        self.logger.info("Getting raw classification outputs")
        return self.raw_classification_outputs

    def get_raw_theme_results(self) -> Dict[str, Dict[str, Any]]:
        """Retrieves raw theme analysis results for all processed abstracts.

        Provides access to the complete, unprocessed outputs from the theme recognition
        chain for each abstract.

        Args:
            None

        Returns:
            Dict[str, Dict[str, Any]]: Dictionary where:
                Type: Dict[str, Dict[str, Any]]
                - Keys are DOI strings
                - Values are raw theme analysis results with structure:
                {
                    "themes": ["theme1", "theme2"],
                    "confidence_scores": {
                        "theme1": 0.95,
                        "theme2": 0.85
                    },
                    "analysis": "Theme analysis text...",
                    # Other theme recognition outputs
                }

        Notes:
            - Contains complete theme recognition outputs
            - Includes confidence scores and analysis text
            - Available after theme recognition stage
            - Empty dictionaries for unprocessed DOIs
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
                Type: str
                Can be absolute or relative path.

        Returns:
            Self: Returns self for method chaining.
                Type: :class:`academic_metrics.AI.AbstractClassifier.AbstractClassifier`

        Notes:
            Output Format:
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
                Type: str
                Can be absolute or relative path.

        Returns:
            Self: Returns self for method chaining.
                Type: :class:`academic_metrics.AI.AbstractClassifier.AbstractClassifier`

        Notes:
            Output Format:
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
