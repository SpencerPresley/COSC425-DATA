# abstract_classifier_factory.py
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from academic_metrics.utils.taxonomy_util import Taxonomy
    from typing import Dict

from academic_metrics.AI.AbstractClassifier import AbstractClassifier


class ClassifierFactory:
    def __init__(self, taxonomy: Taxonomy, ai_api_key: str):
        self.taxonomy = taxonomy
        self.ai_api_key = ai_api_key

    def abstract_classifier_factory(
        self,
        doi_abstract_dict: Dict[str, str],
    ) -> AbstractClassifier:
        return AbstractClassifier(
            taxonomy=self.taxonomy,
            doi_to_abstract_dict=doi_abstract_dict,
            api_key=self.ai_api_key,
        )
