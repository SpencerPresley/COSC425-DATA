# abstract_classifier_factory.py
from __future__ import annotations

from typing import TYPE_CHECKING, Optional
import logging
import os

if TYPE_CHECKING:
    from academic_metrics.utils.taxonomy_util import Taxonomy
    from typing import Dict

from academic_metrics.AI.AbstractClassifier import AbstractClassifier
from academic_metrics.constants import LOG_DIR_PATH


class ClassifierFactory:
    def __init__(
        self,
        taxonomy: Taxonomy,
        ai_api_key: str,
    ):
        self.log_file_path = os.path.join(
            LOG_DIR_PATH, "abstract_classifier_factory.log"
        )
        # Set up logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        if self.logger.handlers:
            self.logger.handlers = []

        # Add handler if none exists
        if not self.logger.handlers:
            handler = logging.FileHandler(self.log_file_path)
            handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        self.logger.info("Initializing ClassifierFactory")

        self.taxonomy = taxonomy
        self.ai_api_key = ai_api_key

        self.logger.info("ClassifierFactory initialized successfully")

    def abstract_classifier_factory(
        self,
        doi_abstract_dict: Dict[str, str],
    ) -> AbstractClassifier:
        self.logger.info("Creating AbstractClassifier")
        classifier = AbstractClassifier(
            taxonomy=self.taxonomy,
            doi_to_abstract_dict=doi_abstract_dict,
            api_key=self.ai_api_key,
        )
        self.logger.info("AbstractClassifier created successfully")
        return classifier
