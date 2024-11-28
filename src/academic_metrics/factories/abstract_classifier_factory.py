# abstract_classifier_factory.py
from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from academic_metrics.utils.taxonomy_util import Taxonomy

from academic_metrics.AI import AbstractClassifier
from academic_metrics.configs import (
    configure_logging,
    DEBUG,
)


class ClassifierFactory:
    """Factory for creating AbstractClassifier instances.

    Attributes:
        logger (logging.Logger): Logger for the factory.
        taxonomy (Taxonomy): Taxonomy for the classifier.
        ai_api_key (str): API key for the classifier.

    Methods:
        abstract_classifier_factory(
            self,
            doi_abstract_dict: Dict[str, str],
            extra_context: dict | None = None,
            pre_classification_model: str | None = None,
            classification_model: str | None = None,
            theme_model: str | None = None,
        ) -> AbstractClassifier:
            Creates an AbstractClassifier instance.
    """

    def __init__(
        self,
        taxonomy: Taxonomy,
        ai_api_key: str,
    ):
        self.logger = configure_logging(
            module_name=__name__,
            log_file_name="abstract_classifier_factory",
            log_level=DEBUG,
        )

        self.logger.info("Initializing ClassifierFactory")

        self.taxonomy: Taxonomy = taxonomy
        self.ai_api_key: str = ai_api_key

        self.logger.info("ClassifierFactory initialized successfully")

    def abstract_classifier_factory(
        self,
        doi_abstract_dict: Dict[str, str],
        extra_context: dict | None = None,
        pre_classification_model: str | None = "gpt-4o-mini",
        classification_model: str | None = "gpt-4o-mini",
        theme_model: str | None = "gpt-4o-mini",
    ) -> AbstractClassifier:
        """Creates an AbstractClassifier instance.

        Args:
            doi_abstract_dict (Dict[str, str]): Dictionary of DOIs and abstracts.
            extra_context (dict | None): Extra context for the classifier.
            pre_classification_model (str | None): Pre-classification model for the classifier.
            classification_model (str | None): Classification model for the classifier.
            theme_model (str | None): Theme model for the classifier.

        Returns:
            classifier (AbstractClassifier): An AbstractClassifier instance.
        """
        self.logger.info("Creating AbstractClassifier")
        classifier: AbstractClassifier = AbstractClassifier(
            taxonomy=self.taxonomy,
            doi_to_abstract_dict=doi_abstract_dict,
            api_key=self.ai_api_key,
            extra_context=extra_context,
            pre_classification_model=pre_classification_model,
            classification_model=classification_model,
            theme_model=theme_model,
        )
        self.logger.info("AbstractClassifier created successfully")
        return classifier
