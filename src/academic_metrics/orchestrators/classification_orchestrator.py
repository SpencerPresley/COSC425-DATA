from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Callable, Dict, List, Tuple, TypeAlias

from pylatexenc.latex2text import LatexNodes2Text
from unidecode import unidecode

from academic_metrics.AI import AbstractClassifier
from academic_metrics.configs import (
    configure_logging,
    DEBUG,
)
from academic_metrics.enums import AttributeTypes

if TYPE_CHECKING:
    from academic_metrics.utils import Utilities

ClassificationResultsDict: TypeAlias = Dict[str, List[str]]
"""Type alias for a dictionary mapping DOIs to lists of classification results.

This type alias is used to represent the return type of the 
:meth:`~academic_metrics.AI.AbstractClassifier.get_classification_results_by_doi` method.
"""

ClassificationResultsTuple: TypeAlias = Tuple[
    List[str], List[str], List[str], List[str]
]
"""Type alias for a tuple containing lists of classification results.

This type alias is used to represent the return type of the 
:meth:`~academic_metrics.AI.AbstractClassifier.get_classification_results_by_doi` method.

Notes:
    - Format of the tuple is (top_categories, mid_categories, low_categories, themes)
"""


class ClassificationOrchestrator:
    """Manages the classification process for research abstracts.

    Orchestrates the process of extracting DOIs and abstracts from research metadata,
    classifying them using AbstractClassifier, and integrating results back into
    the original data. Tracks unclassified items for monitoring.

    Attributes:
        abstract_classifier_factory (Callable[..., AbstractClassifier]): Factory function for AbstractClassifier instances.
        taxonomy (Taxonomy): Classification hierarchy for AbstractClassifier.
        utilities (Utilities): Utilities for attribute extraction.
        ai_api_key (str): API key for AI service access.
        unclassified_item_count (int): Count of unclassified items.
            Type: int
        unclassified_dois (List): DOIs of unclassified items.
            Type: List[str]
        unclassified_abstracts (List): Abstracts of unclassified items.
            Type: List[str]
        unclassified_doi_abstract_dict (Dict): Maps unclassified DOIs to abstracts.
            Type: Dict[str, str]
        unclassified_items (List): Complete metadata of unclassified items.
            Type: List[Dict[str, Any]]
        unclassified_details (Dict): Organized unclassified data.
            Type: Dict[str, Union[List[str], List[Dict[str, Any]]]]
            Contains:
            - dois: List of unclassified DOIs
            - abstracts: List of unclassified abstracts
            - items: List of unclassified metadata items

    Methods:
        run_classification() -> List[Dict]: Processes and classifies a list of research metadata dictionaries.
        get_unclassified_item_count() -> int: Returns the number of unclassified items.
        get_unclassified_dois() -> List[str]: Returns the DOIs of unclassified items.
        get_unclassified_abstracts() -> List[str]: Returns the abstracts of unclassified items.
        get_unclassified_doi_abstract_dict() -> Dict[str, str]: Returns the DOI to abstract mapping dictionary for unclassified items.
        get_unclassified_items() -> List[Dict]: Returns the unclassified items.
        get_unclassified_details_dict() -> Dict: Returns the details of unclassified items.
        _classification_orchestrator() -> List[Dict]: Core classification logic for processing research metadata.
        _inject_categories() -> None: Adds classification results to a research metadata dictionary.
        _extract_categories() -> ClassificationResultsDict | ClassificationResultsTuple: Gets classification results for a specific DOI.
        _make_doi_abstract_dict() -> Dict[str, str]: Creates a DOI to abstract mapping dictionary.
        _retrieve_doi_abstract() -> Tuple[str, str]: Extracts DOI and abstract from a research metadata dictionary.
        _update_classified_instance_variables() -> None: Updates tracking variables for unclassified items.
        _set_classification_ran_true() -> None: Sets the classification ran flag to true.
        _has_ran_classification() -> bool: Checks if classification has been run.
        _validate_classification_ran() -> None: Validates if classification has been run.
        _normalize_abstract() -> str: Normalizes an abstract by removing LaTeX and converting any resulting unicode to ASCII.
    """

    def __init__(
        self,
        abstract_classifier_factory: Callable[[Dict[str, str]], AbstractClassifier],
        utilities: Utilities,
    ):
        """Initialize the ClassificationOrchestrator.

        Sets up the orchestrator with required dependencies for classifying research
        abstracts and managing the classification process.

        Args:
            abstract_classifier_factory (Callable): Factory function for AbstractClassifier.
                Type: Callable[[Dict[str, str]], :class:`~academic_metrics.AI.abstract_classifier.AbstractClassifier`]
            utilities (Utilities): Utilities instance for attribute extraction.
                Type: :class:`~academic_metrics.utils.utilities.Utilities`

        Returns:
            None

        Notes:
            - Initializes tracking variables for unclassified items
            - Sets up classification status flags
            - Prepares data structures for results
            - Validates factory function compatibility
        """
        self.logger = configure_logging(
            module_name=__name__,
            log_file_name="classification_orchestrator",
            log_level=DEBUG,
        )

        self.abstract_classifier_factory = abstract_classifier_factory
        self.utilities = utilities

        # flag to check if classification has been run to provide a method for which to prevent retrieval
        # of unclassified attributes before classification has been ran
        self._classification_ran: bool = False

        self.unclassified_item_count: int = 0
        self.unclassified_dois: List[str] = []
        self.unclassified_abstracts: List[str] = []
        self.unclassified_doi_abstract_dict: Dict[str, str] = {}
        self.unclassified_items: List[Dict] = []
        self.unclassified_details_dict: Dict = {
            "dois": [],
            "abstracts": [],
            "items": [],
        }

    def run_classification(
        self,
        data: List[Dict],
        pre_classification_model: str | None = "gpt-4o-mini",
        classification_model: str | None = "gpt-4o-mini",
        theme_model: str | None = "gpt-4o-mini",
    ) -> List[Dict]:
        """Processes and classifies a list of research metadata dictionaries.

        Extracts abstracts from research metadata, classifies them using specified
        AI models, and injects the classification results back into the original data.

        Args:
            data (list): List of dictionaries containing research metadata.
                Type: List[Dict[str, Any]]
            pre_classification_model (str | None): Model for pre-classification processing.
                Type: str | None
                Defaults to "gpt-4o-mini"
            classification_model (str | None): Model for main classification.
                Type: str | None
                Defaults to "gpt-4o-mini"
            theme_model (str | None): Model for theme extraction.
                Type: str | None
                Defaults to "gpt-4o-mini"

        Returns:
            List: Modified data with classifications injected.
                Type: List[Dict[str, Any]]
                Includes:
                - Original metadata
                - Classification results
                - Theme information
                - Processing status

        Notes:
            - Processes each item sequentially
            - Tracks unclassified items
            - Handles missing abstracts
            - Updates internal statistics
            - Maintains original data structure
        """
        classified_data = self._classification_orchestrator(
            data,
            pre_classification_model=pre_classification_model,
            classification_model=classification_model,
            theme_model=theme_model,
        )
        self._set_classification_ran_true()
        return classified_data

    def get_unclassified_item_count(self) -> int:
        """Gets the number of unclassified items.

        Retrieves the count of items that could not be classified during the
        classification process.

        Returns:
            int: Number of unclassified items.
                Type: int

        Raises:
            RuntimeError: If classification has not been run yet

        Notes:
            - Validates classification status
            - Returns current count
            - Includes all unclassified types
            - Requires prior classification run
        """
        self._validate_classification_ran(self._has_ran_classification())
        return self.unclassified_item_count

    def get_unclassified_dois(self) -> List[str]:
        """Gets the DOIs of unclassified items.

        Retrieves the list of Digital Object Identifiers (DOIs) for items that
        could not be classified during the classification process.

        Returns:
            List: List of unclassified DOIs.
                Type: List[str]
                Empty list if all items were classified.

        Raises:
            RuntimeError: If classification has not been run yet

        Notes:
            - Validates classification status
            - Returns unique DOIs only
            - Maintains original DOI format
            - Requires prior classification run
        """
        self._validate_classification_ran(self._has_ran_classification())
        return self.unclassified_dois

    def get_unclassified_abstracts(self) -> List[str]:
        """Gets the abstracts of unclassified items.

        Retrieves the list of research abstracts for items that could not be
        classified during the classification process.

        Returns:
            List: List of unclassified abstracts.
                Type: List[str]
                Empty list if all items were classified.

        Raises:
            RuntimeError: If classification has not been run yet

        Notes:
            - Validates classification status
            - Returns normalized abstracts
            - Maintains text formatting
            - Requires prior classification run
            - May include empty abstracts
        """
        self._validate_classification_ran(self._has_ran_classification())
        return self.unclassified_abstracts

    def get_unclassified_doi_abstract_dict(self) -> Dict[str, str]:
        """Gets the DOI to abstract mapping dictionary for unclassified items.

        Retrieves a dictionary that maps Digital Object Identifiers (DOIs) to their
        corresponding abstracts for items that could not be classified.

        Returns:
            Dict: Dictionary mapping unclassified DOIs to abstracts.
                Type: Dict[str, str]
                Keys: DOIs (str)
                Values: Abstracts (str)
                Empty dict if all items were classified.

        Raises:
            RuntimeError: If classification has not been run yet

        Notes:
            - Validates classification status
            - Maintains DOI-abstract relationships
            - Contains normalized abstracts
            - Requires prior classification run
            - Preserves original DOI format
        """
        self._validate_classification_ran(self._has_ran_classification())
        return self.unclassified_doi_abstract_dict

    def get_unclassified_items(self) -> List[Dict]:
        """Gets the unclassified items.

        Retrieves the complete list of research items that could not be classified,
        including all their original metadata.

        Returns:
            List: List of unclassified items with full metadata.
                Type: List[Dict[str, Any]]
                Empty list if all items were classified.
                Each dict contains complete item metadata.

        Raises:
            RuntimeError: If classification has not been run yet

        Notes:
            - Validates classification status
            - Returns complete metadata
            - Preserves original structure
            - Requires prior classification run
            - Maintains all item attributes
        """
        self._validate_classification_ran(self._has_ran_classification())
        return self.unclassified_items

    def get_unclassified_details_dict(self) -> Dict:
        """Gets the details of unclassified items.

        Retrieves a comprehensive dictionary containing organized information about
        all unclassified items, including DOIs, abstracts, and complete metadata.

        Returns:
            Dict: Organized details of unclassified items.
                Type: Dict[str, Union[List[str], List[Dict[str, Any]]]]
                Contains:
                - dois: List[str] - Unclassified DOIs
                - abstracts: List[str] - Unclassified abstracts
                - items: List[Dict] - Complete metadata

        Raises:
            RuntimeError: If classification has not been run yet

        Notes:
            - Validates classification status
            - Provides structured access
            - Groups related information
            - Requires prior classification run
            - Maintains data relationships
        """
        self._validate_classification_ran(self._has_ran_classification())
        return self.unclassified_details_dict

    def _classification_orchestrator(
        self,
        data: List[Dict],
        pre_classification_model: str | None = "gpt-4o-mini",
        classification_model: str | None = "gpt-4o-mini",
        theme_model: str | None = "gpt-4o-mini",
    ) -> List[Dict]:
        """Core classification logic for processing research metadata.

        Implements the main classification workflow, processing research metadata
        through multiple stages of classification and theme extraction.

        Args:
            data (List): List of dictionaries containing research metadata.
                Type: List[Dict[str, Any]]
            pre_classification_model (str | None): Model for pre-classification processing.
                Type: str | None
                Defaults to "gpt-4o-mini"
            classification_model (str | None): Model for main classification.
                Type: str | None
                Defaults to "gpt-4o-mini"
            theme_model (str | None): Model for theme extraction.
                Type: str | None
                Defaults to "gpt-4o-mini"

        Returns:
            List: Modified data with classifications and themes injected.
                Type: List[Dict[str, Any]]
                Includes:
                - Original metadata
                - Classification results
                - Theme information
                - Processing status

        Notes:
            - Processes items sequentially
            - Handles classification failures
            - Tracks unclassified items
            - Updates internal statistics
            - Maintains data integrity
            - Manages model selection
        """
        i = 0

        # This must be a `while` loop because the list `data` is modified during iteration.
        # Specifically, items may be removed (via `pop`) when an error occurs. A `for` loop
        # uses an iterator tied to the list's initial state and does not account for changes
        # to the list structure. Modifying the list while using a `for` loop would cause
        # skipped items, incorrect indexing, or runtime errors.
        #
        # With a `while` loop, we have full control over the index (`i`). If an item is
        # removed, the remaining items shift, and the loop naturally rechecks the current
        # index without skipping. This ensures every item is processed exactly once, and
        # the logic remains robust despite the dynamic list modifications.
        #
        # Do not attempt to use a `for` loop here—it will not handle these modifications safely.
        while i < len(data):
            item = data[i]

            try:
                doi, abstract, extra_context = self._get_classification_dependencies(
                    item
                )
                normalized_abstract: str = self._normalize_abstract(abstract)
                doi_abstract_dict: Dict[str, str] = self._make_doi_abstract_dict(
                    doi, normalized_abstract
                )
                if not doi_abstract_dict:
                    self._update_classified_instance_variables(
                        item=item, doi=doi, abstract=abstract
                    )
                    i += 1
                    continue

                classifier: AbstractClassifier = self.abstract_classifier_factory(
                    doi_abstract_dict=doi_abstract_dict,
                    extra_context=extra_context,
                    pre_classification_model=pre_classification_model,
                    classification_model=classification_model,
                    theme_model=theme_model,
                )

                classifier.classify()

                self._inject_categories(
                    data=item, categories=self._extract_categories(doi, classifier)
                )

                i += 1

            except Exception as e:
                self.logger.error(f"Error processing item {i}: {e}")
                self.logger.error(f"Popping the item at index {i} from data")
                self.logger.error(f"Full error traceback:", exc_info=True)
                self.logger.error(f"Problem item: {item}")
                data.pop(i)

        return data

    def _inject_categories(
        self,
        data: Dict,
        categories: ClassificationResultsDict | ClassificationResultsTuple,
    ) -> None:
        """Adds classification results to a research metadata dictionary.

        Injects classification categories and themes into the provided metadata
        dictionary, handling both dictionary and tuple result formats.

        Args:
            data (Dict): Research metadata dictionary.
                Type: Dict[str, Any]
            categories (Union): Classification results including categories and themes.
                Type: Union[ClassificationResultsDict, ClassificationResultsTuple]
                Where:
                - ClassificationResultsDict: Dict[str, List[str]]
                    Format: {
                        "top_categories": List[str],
                        "mid_categories": List[str],
                        "low_categories": List[str],
                        "themes": List[str]
                    }
                - ClassificationResultsTuple: Tuple[List[str], List[str], List[str], List[str]]
                    Format: (
                        top_level_categories: List[str],
                        mid_level_categories: List[str],
                        low_level_categories: List[str],
                        themes: List[str]
                    )

        Raises:
            ValueError: If categories is neither a dict nor a tuple

        Notes:
            - Modifies input dictionary in-place
            - Handles both result formats
            - Preserves existing metadata
            - Validates category structure
            - Maintains hierarchical relationships
            - Provides default empty lists for missing dictionary keys
        """
        # Check if it's a dictionary (Dict[str, List[str]])
        # Format: {
        #     "top_categories": List[str],
        #     "mid_categories": List[str],
        #     "low_categories": List[str],
        #     "themes": List[str]
        # }
        if isinstance(categories, dict):
            data["categories"] = {}
            data["categories"]["top"] = categories.get("top_categories", [])
            data["categories"]["mid"] = categories.get("mid_categories", [])
            data["categories"]["low"] = categories.get("low_categories", [])
            data["themes"] = categories.get("themes", [])
        # Otherwise it must be a tuple (Tuple[List[str], List[str], List[str], List[str]])
        # Format: (
        #     top_level_categories: List[str],
        #     mid_level_categories: List[str],
        #     low_level_categories: List[str],
        #     themes: List[str]
        # )
        elif isinstance(categories, tuple):
            data["categories"] = {}
            data["categories"]["top"] = categories[0]
            data["categories"]["mid"] = categories[1]
            data["categories"]["low"] = categories[2]
            data["themes"] = categories[3]
        else:
            raise ValueError("Invalid categories format")

    def _extract_categories(
        self, doi: str, classifier: AbstractClassifier
    ) -> ClassificationResultsDict | ClassificationResultsTuple:
        """Gets classification results for a specific DOI.

        Retrieves the classification categories and themes for a given DOI using
        the provided classifier instance. Supports both dictionary and tuple result formats.

        Args:
            doi (str): DOI identifier for the research item.
                Type: str
            classifier (AbstractClassifier): Classifier instance that performed classification.
                Type: :class:`~academic_metrics.AI.abstract_classifier.AbstractClassifier`

        Returns:
            Union: Classification results including categories and themes.
                Type: Union[:data:`~academic_metrics.orchestrators.classification_orchestrator.ClassificationResultsDict`,
                          :data:`~academic_metrics.orchestrators.classification_orchestrator.ClassificationResultsTuple`]
                Where:
                - :data:`~academic_metrics.orchestrators.classification_orchestrator.ClassificationResultsDict`:
                    Format: {
                        "top_categories": List[str],
                        "mid_categories": List[str],
                        "low_categories": List[str],
                        "themes": List[str]
                    }
                - :data:`~academic_metrics.orchestrators.classification_orchestrator.ClassificationResultsTuple`:
                    Format: (
                        top_level_categories: List[str],
                        mid_level_categories: List[str],
                        low_level_categories: List[str],
                        themes: List[str]
                    )

        Notes:
            - Utilizes classifier to obtain results
            - Supports multiple result formats
            - Ensures DOI is valid and classified
            - Handles missing classification gracefully
        """
        # .get_classification_results_by_doi() has a argument of return_type that can be set to either a dictionary or a tuple
        # By default it returns a dict, it you want a tuple you can do return_type=tuple
        return classifier.get_classification_results_by_doi(doi)

    def _make_doi_abstract_dict(self, doi: str, abstract: str) -> Dict[str, str]:
        """Creates a DOI to abstract mapping dictionary.

        Constructs a dictionary that maps a given DOI to its corresponding abstract,
        ensuring both values are provided.

        Args:
            doi (str): DOI identifier for the research item.
                Type: str
            abstract (str): Research abstract text.
                Type: str

        Returns:
            dict: Dictionary mapping DOI to abstract.
                Type: Dict[str, str]
                Format: {doi: abstract}

        Raises:
            ValueError: If either DOI or abstract is missing

        Notes:
            - Ensures both DOI and abstract are non-empty
            - Provides a simple mapping structure
            - Validates input before mapping
        """
        if not doi or not abstract:
            raise ValueError("Both DOI and abstract must be provided and non-empty.")
        return {doi: abstract}

    def _get_classification_dependencies(self, item: Dict) -> Tuple[str, str, dict]:
        """Extracts DOI, abstract, and extra context from a research metadata dictionary.

        Uses the utilities module to safely extract required attributes from the
        research metadata, handling missing or invalid values.

        Args:
            item (dict): Research metadata dictionary.
                Type: Dict[str, Any]

        Returns:
            tuple: DOI, abstract, and extra context.
                Type: Tuple[str, str, dict]
                Format: (
                    doi: str | None,
                    abstract: str | None,
                    extra_context: dict | None
                )

        Notes:
            - Uses :class:`~academic_metrics.utils.utilities.Utilities` for extraction
            - Extracts attributes:
                - :data:`~academic_metrics.enums.enums.AttributeTypes.CROSSREF_DOI`
                - :data:`~academic_metrics.enums.enums.AttributeTypes.CROSSREF_ABSTRACT`
                - :data:`~academic_metrics.enums.enums.AttributeTypes.CROSSREF_EXTRA_CONTEXT`
            - Returns None for any missing attributes
            - Preserves original attribute values
            - Handles missing or malformed data gracefully
        """
        result: Dict[AttributeTypes, Tuple[bool, str]] = self.utilities.get_attributes(
            item,
            [
                AttributeTypes.CROSSREF_DOI,
                AttributeTypes.CROSSREF_ABSTRACT,
                AttributeTypes.CROSSREF_EXTRA_CONTEXT,
            ],
        )
        doi: str = (
            result[AttributeTypes.CROSSREF_DOI][1]
            if result[AttributeTypes.CROSSREF_DOI][0]
            else None
        )
        abstract: str = (
            result[AttributeTypes.CROSSREF_ABSTRACT][1]
            if result[AttributeTypes.CROSSREF_ABSTRACT][0]
            else None
        )
        extra_context: dict = (
            result[AttributeTypes.CROSSREF_EXTRA_CONTEXT][1]
            if result[AttributeTypes.CROSSREF_EXTRA_CONTEXT][0]
            else None
        )
        return doi, abstract, extra_context

    def _update_classified_instance_variables(
        self, item: Dict, doi: str, abstract: str
    ) -> None:
        """Updates tracking variables for unclassified items.

        Maintains multiple tracking collections for items that couldn't be classified,
        ensuring consistent record-keeping across different data structures.

        Args:
            item (dict): Research metadata dictionary.
                Type: Dict[str, Any]
            doi (str): DOI identifier.
                Type: str | None
            abstract (str): Research abstract text.
                Type: str | None

        Returns:
            None

        Notes:
            - Updates instance variables:
                - :attr:`~academic_metrics.orchestrators.classification_orchestrator.ClassificationOrchestrator.unclassified_item_count`
                - :attr:`~academic_metrics.orchestrators.classification_orchestrator.ClassificationOrchestrator.unclassified_dois`
                - :attr:`~academic_metrics.orchestrators.classification_orchestrator.ClassificationOrchestrator.unclassified_abstracts`
                - :attr:`~academic_metrics.orchestrators.classification_orchestrator.ClassificationOrchestrator.unclassified_doi_abstract_dict`
                - :attr:`~academic_metrics.orchestrators.classification_orchestrator.ClassificationOrchestrator.unclassified_items`
                - :attr:`~academic_metrics.orchestrators.classification_orchestrator.ClassificationOrchestrator.unclassified_details_dict`
            - Handles missing values by using "NULL" placeholder
            - Maintains parallel data structures for different access patterns
            - Preserves original metadata in unclassified items list
            - Increments unclassified item counter
        """
        self.unclassified_item_count += 1
        (
            self.unclassified_dois.append(doi)
            if doi
            else self.unclassified_dois.append("NULL")
        )
        (
            self.unclassified_abstracts.append(abstract)
            if abstract
            else self.unclassified_abstracts.append("NULL")
        )
        self.unclassified_doi_abstract_dict[doi] = abstract
        self.unclassified_items.append(item)
        (
            self.unclassified_details_dict["dois"].append(doi)
            if doi
            else self.unclassified_details_dict["dois"].append("NULL")
        )
        (
            self.unclassified_details_dict["abstracts"].append(abstract)
            if abstract
            else self.unclassified_details_dict["abstracts"].append("NULL")
        )
        self.unclassified_details_dict["items"].append(item)

    def _set_classification_ran_true(self) -> None:
        """Sets the classification ran flag to true.

        Updates the internal state to indicate that classification process
        has been executed.

        Args:
            None

        Returns:
            None

        Notes:
            - Updates :attr:`~academic_metrics.orchestrators.classification_orchestrator.ClassificationOrchestrator._classification_ran`
            - Used for validation checks
            - State cannot be reset to false
        """
        self._classification_ran: bool = True

    def _has_ran_classification(self) -> bool:
        """Checks if classification has been run.

        Returns
        """
        return self._classification_ran

    def _validate_classification_ran(self, classification_ran: bool) -> None:
        """Checks if classification has been run.

        Verifies whether the classification process has been executed by
        checking the internal state flag.

        Args:
            None

        Returns:
            bool: True if classification has been run, False otherwise.
                Type: bool

        Notes:
            - Reads :attr:`~academic_metrics.orchestrators.classification_orchestrator.ClassificationOrchestrator._classification_ran`
            - Used for validation before accessing results
            - Cannot detect if classification is currently running
        """
        if not classification_ran:
            raise RuntimeError(
                "Classification has not been run yet. "
                "Call run_classification() on your data before attempting to retrieve unclassified attributes. "
                "Data should be a list of loaded crossref JSON objects."
            )

    def _normalize_abstract(self, abstract: str) -> str:
        """Normalizes an abstract by removing LaTeX and converting any resulting unicode to ASCII.

        Processes research abstract text through two stages:
        1. Converts LaTeX notation to unicode text
        2. Converts unicode characters to ASCII equivalents

        Args:
            abstract (str): Research abstract text.
                Type: str
                May contain LaTeX math notation and unicode characters.

        Returns:
            str: Normalized abstract text.
                Type: str
                Contains only ASCII characters.

        Notes:
            - Uses :class:`~pylatexenc.latex2text.LatexNodes2Text` for LaTeX conversion
            - Uses :pypi:`Unidecode` for unicode to ASCII conversion
            - Handles mathematical notation
            - Preserves text structure
            - Removes special characters
            - Math mode set to "text" for consistent conversion
        """
        converter: LatexNodes2Text = LatexNodes2Text(math_mode="text")
        unicode_abstract: str = converter.latex_to_text(abstract)
        ascii_abstract: str = unidecode(unicode_abstract)
        return ascii_abstract
