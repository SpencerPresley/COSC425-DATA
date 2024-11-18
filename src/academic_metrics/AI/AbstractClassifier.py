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
from academic_metrics.constants import LOG_DIR_PATH

if TYPE_CHECKING:
    from academic_metrics.utils.taxonomy_util import Taxonomy


class AbstractClassifier:
    """
    Process research paper abstracts through classification and theme analysis.

    Handles the complete pipeline of abstract processing including method extraction,
    sentence analysis, abstract summarization, hierarchical taxonomy classification,
    and theme recognition. Results are stored both as raw outputs and processed
    classification results.

    Attributes:
        taxonomy (Taxonomy): Taxonomy instance containing the classification hierarchy
        doi_to_abstract_dict (Dict[str, str]): Dictionary mapping DOIs to abstract texts
        api_key (str): API key for LLM access
        logger (Logger): Logger instance for tracking operations
        classification_results (Dict[str, Dict]): Processed classification results by DOI
        raw_classification_outputs (List[Dict]): Raw outputs from classification chain
        raw_theme_outputs (Dict[str, Dict]): Raw theme analysis results by DOI
        pre_classification_chain_manager (ChainManager): Chain for pre-classification steps
        classification_chain_manager (ChainManager): Chain for classification
        theme_chain_manager (ChainManager): Chain for theme recognition

    Example:
        >>> from academic_metrics.utils.taxonomy_util import Taxonomy
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
        >>> # Save results
        >>> classifier.save_classification_results("classification_results.json")
        >>> classifier.save_raw_theme_results("theme_results.json")
        >>> classifier.save_raw_classification_results("raw_outputs.json")

    Raises:
        TypeError: If api_key is missing or not convertible to string

    Methods:
        Public Methods:
            classify()
                Processes all abstracts through the complete pipeline including pre-classification,
                classification, and theme analysis. Updates classification_results and raw outputs.

            get_classification_results_by_doi(doi: str, return_type: type[dict] | type[tuple] = dict) -> Union[Tuple[str, ...], Dict[str, Any]]
                Retrieves all categories and themes for a specific abstract, organized by
                taxonomy level (top, mid, low) and themes.

            get_raw_classification_outputs() -> List[Dict[str, Any]]
                Returns the raw classification outputs from all processed abstracts.

            get_raw_theme_results() -> Dict[str, Dict[str, Any]]
                Returns the raw theme analysis results for all processed abstracts.

            save_classification_results(output_path: str) -> AbstractClassifier
                Saves processed classification results to JSON file. Returns self for chaining.

            save_raw_classification_results(output_path: str) -> AbstractClassifier
                Saves raw classification outputs to JSON file. Returns self for chaining.

            save_raw_theme_results(output_path: str) -> AbstractClassifier
                Saves raw theme analysis results to JSON file. Returns self for chaining.

        Private Methods:
            _run_initial_api_key_validation(api_key: str)
                Validates API key format and presence.

            _initialize_chain_manager() -> ChainManager
                Creates new ChainManager instance with configured settings.

            _add_method_extraction_layer() -> AbstractClassifier
                Adds method extraction processing layer to chain manager.

            _add_sentence_analysis_layer() -> AbstractClassifier
                Adds sentence analysis processing layer to chain manager.

            _add_summary_layer() -> AbstractClassifier
                Adds abstract summarization layer to chain manager.

            _add_classification_layer() -> AbstractClassifier
                Adds classification processing layer to chain manager.

            _add_theme_recognition_layer() -> AbstractClassifier
                Adds theme recognition processing layer to chain manager.

            classify_abstract(abstract: str, doi: str, prompt_variables: Dict[str, Any],
                            level: str = "top", parent_category = None) -> Dict[str, Any]
                Recursively classifies an abstract through taxonomy levels.

            extract_classified_categories(classification_output: ClassificationOutput) -> List[str]
                Extracts classified categories from classification output.
    """

    def __init__(
        self,
        taxonomy: Taxonomy,
        doi_to_abstract_dict: Dict[str, str],
        api_key: str,
        log_to_console: bool = True,
    ) -> None:

        # Set up logger
        log_file_path: str = os.path.join(LOG_DIR_PATH, "abstract_classifier.log")
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []
        self.log_to_console: bool = log_to_console

        # Add handler if none exists
        if not self.logger.handlers:
            handler: logging.FileHandler = logging.FileHandler(log_file_path)
            handler.setLevel(logging.DEBUG)
            formatter: logging.Formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            console_handler: Optional[logging.StreamHandler] = (
                logging.StreamHandler() if self.log_to_console else None
            )
            if console_handler:
                console_handler.setFormatter(formatter)
                self.logger.addHandler(console_handler)
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        self.logger.info("Initializing AbstractClassifier")
        self.logger.info("Performing setup")

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
            self._initialize_chain_manager()
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
            self._initialize_chain_manager()
        )
        self._add_classification_layer(self.classification_chain_manager)
        self.logger.info("Classification chain manager initialized and layers added")

        self.logger.info(
            "Initializing and adding layers to theme recognition chain manager"
        )
        self.theme_chain_manager: ChainManager = self._initialize_chain_manager()
        self._add_theme_recognition_layer(self.theme_chain_manager)
        self.logger.info("Theme recognition chain manager initialized and layers added")

    def _run_initial_api_key_validation(self, api_key: str) -> None:
        """Validates the API key format and presence.

        Performs initial validation of the API key to ensure it exists and can be
        converted to a string type.

        Args:
            api_key: The API key to validate.

        Raises:
            TypeError: If the API key is empty/None or cannot be converted to string.

        Example:
            >>> classifier._run_initial_api_key_validation("valid-api-key")  # passes
            >>> classifier._run_initial_api_key_validation("")  # raises TypeError
            >>> classifier._run_initial_api_key_validation(None)  # raises TypeError
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

    def _initialize_chain_manager(self) -> ChainManager:
        """Initializes a new ChainManager instance with default settings.

        Creates a new ChainManager configured with specific LLM model settings
        for processing abstract analysis chains.

        Returns:
            ChainManager: A new ChainManager instance
        """
        # TODO: Make these configurable
        return ChainManager(
            llm_model="gpt-4o-mini",
            api_key=self.api_key,
            llm_temperature=0.7,
            log_to_console=self.log_to_console,
        )

    def _add_method_extraction_layer(self, chain_manager: ChainManager) -> Self:
        """
        Adds the method extraction layer to the chain manager

        Returns:
            AbstractClassifier: The AbstractClassifier instance with the method extraction layer added
                - Returns self to enable method chaining
                - see: https://www.geeksforgeeks.org/method-chaining-in-python/
                - specifically '4. Method Chaining in Object-Oriented Programming (OOP)
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
        """
        Adds the sentence analysis layer to the chain manager

        Returns:
            AbstractClassifier: The AbstractClassifier instance with the sentence analysis layer added
                - Returns self to enable method chaining
                - see: https://www.geeksforgeeks.org/method-chaining-in-python/
                - specifically '4. Method Chaining in Object-Oriented Programming (OOP)
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
        """
        Adds the summary layer to the chain manager

        Returns:
            AbstractClassifier: The AbstractClassifier instance with the summary layer added
                - Returns self to enable method chaining
                - see: https://www.geeksforgeeks.org/method-chaining-in-python/
                - specifically '4. Method Chaining in Object-Oriented Programming (OOP)
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
        """
        Adds the classification layer to the chain manager

        Returns:
            AbstractClassifier: The AbstractClassifier instance with the classification layer added
                - Returns self to enable method chaining
                - see: https://www.geeksforgeeks.org/method-chaining-in-python/
                - specifically '4. Method Chaining in Object-Oriented Programming (OOP)
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
        """Adds the theme recognition layer to the chain manager

        Returns:
            AbstractClassifier: The AbstractClassifier instance with the theme recognition layer added
                - Returns self to enable method chaining
                - see: https://www.geeksforgeeks.org/method-chaining-in-python/
                - specifically '4. Method Chaining in Object-Oriented Programming (OOP)
        """
        chain_manager.add_chain_layer(
            system_prompt=THEME_RECOGNITION_SYSTEM_MESSAGE,
            human_prompt=HUMAN_MESSAGE_PROMPT,
            parser_type="json",
            pydantic_output_model=ThemeAnalysis,
            output_passthrough_key_name="theme_output",
        )
        return self

    def get_classification_results_by_doi(
        self, doi: str, return_type: type[dict] | type[tuple] = dict
    ) -> Union[Tuple[str, ...], Dict[str, Any]]:
        """Retrieves all categories and themes for a specific abstract via a DOI lookup.

        Args:
            doi: The DOI identifier for the abstract to retrieve results for.
            return_type: Return type class (dict or tuple). Defaults to dict.

        Returns:
            Union[Tuple[str, ...], Dict[str, Any]]: Either:
                - If return_type=tuple:
                    Tuple of strings containing all categories and themes in order:
                    (top_categories, mid_categories, low_categories, themes)
                - If return_type=dict:
                    Dictionary containing:
                    - top_categories (List[str]): Top-level taxonomy categories
                    - mid_categories (List[str]): Mid-level taxonomy categories
                    - low_categories (List[str]): Low-level taxonomy categories
                    - themes (List[str]): Identified themes for the abstract

        Example:
            >>> # Get results as dictionary
            >>> results = classifier.get_classification_results_by_doi("10.1234/example")
            >>> print(results["top_categories"])

            >>> # Get results as tuple
            >>> top_cats, mid_cats, low_cats, themes = classifier.get_classification_results_by_doi(
            ...     "10.1234/example",
            ...     return_type=tuple
            ... )
        """
        top_categories: List[str] = []
        mid_categories: List[str] = []
        low_categories: List[str] = []

        abstract_result: Dict[str, Any] = self.classification_results.get(doi, {})

        def extract_categories(result: Dict[str, Any], level: str) -> None:
            """Recursively extracts categories from nested classification results."""
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
        level: str = "top",
        parent_category: Optional[str] = None,
        current_dict: Optional[
            Dict[str, Any]
        ] = None,  # parameter to track current position in defaultdict
    ) -> None:
        """Recursively classifies an abstract through the taxonomy hierarchy.

        Processes an abstract through the classification chain, starting at the top level
        and recursively working down through mid and low levels based on the initial
        classifications. Each level's classification results determine which subcategories
        to evaluate at the next level.

        Args:
            abstract: The text of the abstract to classify
            doi: The DOI identifier for the abstract
            prompt_variables: Dictionary containing variables needed for classification:
                - abstract: The abstract text
                - categories: Available categories for current level
                - Other chain-specific variables (formats, examples, etc.), see classify() method.
            level: Current taxonomy level being processed ("top", "mid", or "low")
            parent_category: The parent category from the previous level (None for top level)
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
                    # current_dict is already the list for this mid category, so just append the classified low category
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

    def extract_classified_categories(
        self, classification_output: ClassificationOutput
    ) -> List[str]:
        """Extracts category names from a classification output object.

        Flattens the nested structure of ClassificationOutput into a simple list of
        category names. Handles multiple classifications within the output object.

        Args:
            classification_output: Pydantic model containing classification results
                Expected structure:
                {
                    "classifications": [
                        {"categories": ["category1", "category2"]},
                        {"categories": ["category3"]}
                    ]
                }

        Returns:
            List[str]: Flattened list of all classified category names
        """
        self.logger.info("Extracting classified categories")
        categories: List[str] = [
            cat
            for classification in classification_output.classifications
            for cat in classification.categories
        ]
        self.logger.info("Extracted classified categories")
        return categories

    def classify(self) -> Self:
        """Orchestrates the complete classification pipeline for all abstracts.

        Processes each abstract through a three-stage pipeline:
        1. Pre-classification: Extracts methods, analyzes sentences, and generates summaries
        2. Classification: Recursively classifies the abstract through taxonomy levels (top->mid->low)
        3. Theme Recognition: Identifies key themes and concepts

        The pipeline uses three separate ChainManager instances:
        - pre_classification_chain_manager: Handles initial abstract analysis
        - classification_chain_manager: Manages hierarchical classification
        - theme_chain_manager: Processes theme recognition

        Results are stored in three class attributes:
        - classification_results: Final processed results including categories and themes
        - raw_classification_outputs: Raw outputs from classification chain
        - raw_theme_outputs: Raw outputs from theme recognition

        Flow:
        1. For each abstract:
            a. Run pre-classification chains (method extraction, sentence analysis, summarization)
            b. Pass enriched results to classification chain
            c. Recursively classify through taxonomy levels
            d. Extract themes using theme recognition chain
            e. Store results in appropriate data structures

        Example:
            >>> classifier = AbstractClassifier(taxonomy, doi_to_abstract_dict, api_key)
            >>> classifier.classify()
            >>> # Results stored in:
            >>> print(classifier.classification_results)  # Processed results
            >>> print(classifier.raw_classification_outputs)  # Raw classification data
            >>> print(classifier.raw_theme_outputs)  # Raw theme data

        Note:
            This method modifies instance state by updating:
            - self.classification_results
            - self.raw_classification_outputs
            - self.raw_theme_outputs
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
            prompt_variables.update(
                {
                    "THEME_RECOGNITION_JSON_FORMAT": THEME_RECOGNITION_JSON_FORMAT,
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
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    def save_classification_results(self, output_path: str) -> Self:
        """Saves processed classification results to a JSON file.

        Args:
            output_path: Path where the JSON file should be saved

        Returns:
            AbstractClassifier: Self reference for method chaining
            
        Example Standalone:
            >>> abstract_classifier = AbstractClassifier(taxonomy, abstract_doi_dict, api_key)
            >>> abstract_classifier.classify()
            >>> abstract_classifier.save_classification_results("results/classifications.json")
            
        Example Method Chain:
            >>> abstract_classifier = AbstractClassifier(taxonomy, abstract_doi_dict, api_key)
            >>> abstract_classifier.classify()\\
            ...          .save_classification_results("results/classifications.json")
        """
        self.logger.info("Saving classification results")
        self._make_dirs_helper(output_path)
        with open(output_path, "w") as f:
            json.dump(self.classification_results, f, indent=4)
        return self

    def get_classification_results_dict(self) -> Dict[str, Dict[str, Any]]:
        """Retrieves processed classification results for all processed abstracts.

        Returns:
            Dict[str, Dict[str, Any]]: Dictionary where:
                - Keys are DOI strings
                - Values are processed classification results
        """
        self.logger.info("Getting classification results")
        return self.classification_results

    def get_raw_classification_outputs(self) -> List[Dict[str, Any]]:
        """Retrieves raw classification outputs from all processed abstracts.

        Returns:
            List[Dict[str, Any]]: List of raw classification outputs, where each output
                contains the complete chain response including prompt variables and
                classification results.

        Example:
            >>> raw_outputs = classifier.get_raw_classification_outputs()
            >>> print(raw_outputs[0])  # First abstract's raw classification data
        """
        self.logger.info("Getting raw classification outputs")
        return self.raw_classification_outputs

    def get_raw_theme_results(self) -> Dict[str, Dict[str, Any]]:
        """Retrieves raw theme analysis results for all processed abstracts.

        Returns:
            Dict[str, Dict[str, Any]]: Dictionary where:
                - Keys are DOI strings
                - Values are raw theme analysis results
        """
        self.logger.info("Getting raw theme results")
        return self.raw_theme_outputs

    def save_raw_classification_results(self, output_path: str) -> Self:
        """Saves raw classification outputs to a JSON file.

        Args:
            output_path: Path where the JSON file should be saved

        Returns:
            AbstractClassifier: Self reference for method chaining

        Example Standalone:
            >>> abstract_classifier = AbstractClassifier(taxonomy, abstract_doi_dict, api_key)
            >>> abstract_classifier.classify()
            >>> abstract_classifier.save_raw_classification_results("debug/raw_classifications.json")
            
        Example Method Chain:
            >>> abstract_classifier = AbstractClassifier(taxonomy, abstract_doi_dict, api_key)
            >>> abstract_classifier.classify()\\
            ...          .save_raw_classification_results("debug/raw_classifications.json")\\
        """
        self.logger.info("Saving classification results")
        self._make_dirs_helper(output_path)
        with open(output_path, "w") as f:
            json.dump(self.raw_classification_outputs, f, indent=4)
        return self

    def save_raw_theme_results(self, output_path: str) -> Self:
        """Saves raw theme analysis results to a JSON file.

        Args:
            output_path: Path where the JSON file should be saved

        Returns:
            AbstractClassifier: Self reference for method chaining
            
        Example Standalone:
            >>> abstract_classifier = AbstractClassifier(taxonomy, abstract_doi_dict, api_key)
            >>> abstract_classifier.classify()
            >>> abstract_classifier.save_raw_theme_results("debug/raw_themes.json")

        Example Method Chain:
            >>> abstract_classifier = AbstractClassifier(taxonomy, abstract_doi_dict, api_key)
            >>> abstract_classifier.classify()\\
            ...          .save_raw_theme_results("debug/raw_themes.json")\\
        """
        self.logger.info("Saving theme results")
        self._make_dirs_helper(output_path)
        with open(output_path, "w") as f:
            json.dump(self.raw_theme_outputs, f, indent=4)
        return self


if __name__ == "__main__":
    # # from academic_metrics.AI.testing_data.abstracts import doi_to_abstract_dict
    # from academic_metrics.utils.taxonomy_util import Taxonomy
    # from dotenv import load_dotenv
    # import os
    # from pylatexenc.latex2text import LatexNodes2Text
    # from unidecode import unidecode

    # load_dotenv()
    # openai_api_key = os.getenv("OPENAI_API_KEY")

    # taxonomy: Taxonomy = Taxonomy()

    # abstract_classifier = AbstractClassifier(
    #     taxonomy=taxonomy,
    #     doi_to_abstract_dict=doi_to_abstract_dict,
    #     api_key=openai_api_key,
    # )
    # abstract_classifier.classify().save_classification_results(
    #     "outputs/classification_results.json"
    # ).save_raw_theme_results(
    #     "outputs/theme_results.json"
    # ).save_raw_classification_results(
    #     "outputs/raw_classification_outputs.json"
    # )
    pass
