import os
import json
from typing import Callable, Dict

from academic_metrics.main import CategoryDataOrchestrator
from academic_metrics.utils import (
    ClassifierFactory,
    WarningManager,
    Taxonomy,
    Utilities,
    APIKeyValidator,
)
from academic_metrics.strategies import StrategyFactory
from academic_metrics.constants import (
    INPUT_FILES_DIR_PATH,
    SPLIT_FILES_DIR_PATH,
    OUTPUT_FILES_DIR_PATH,
)
from academic_metrics.core import ClassificationWrapper


class PipelineRunner:
    def __init__(self, ai_api_key: str):
        self.ai_api_key = ai_api_key
        self.taxonomy = self._create_taxonomy()
        self.warning_manager = self._create_warning_manager()
        self.strategy_factory = self._create_strategy_factory()
        self.utilities = self._create_utilities_instance()
        self.classification_wrapper = self._create_classification_wrapper()

    def run_pipeline(self, make_files: bool = False, extend: bool = False):
        if make_files:
            self._make_files()

        # Load all files into memory
        data = self._load_files()

        # Run classification on all data
        data = self.classification_wrapper.run_classification(data)

        # Process classified data and generate category statistics
        self._create_orchestrator(data=data, extend=extend).run_orchestrator()

    def _create_taxonomy(self) -> Taxonomy:
        return Taxonomy()

    def _create_classifier_factory(self) -> ClassifierFactory:
        return ClassifierFactory(taxonomy=self.taxonomy, ai_api_key=self.ai_api_key)

    def _create_warning_manager(self) -> WarningManager:
        return WarningManager()

    def _create_strategy_factory(self) -> StrategyFactory:
        return StrategyFactory()

    def _create_utilities_instance(self) -> Utilities:
        return Utilities(
            strategy_factory=self.strategy_factory, warning_manager=self.warning_manager
        )

    def _create_classification_wrapper(self) -> ClassificationWrapper:
        return ClassificationWrapper(
            abstract_classifier_factory=self._get_acf_func(),
            utilities=self.utilities,
        )

    def _create_orchestrator(
        self, data: list[dict], extend: bool
    ) -> CategoryDataOrchestrator:
        return CategoryDataOrchestrator(
            data=data,
            output_dir_path=OUTPUT_FILES_DIR_PATH,
            warning_manager=self.warning_manager,
            strategy_factory=self.strategy_factory,
            utilities=self.utilities,
            extend=extend,
        )

    def _get_acf_func(self) -> Callable[[Dict[str, str]], ClassifierFactory]:
        """
        Returns a function that takes a dictionary of DOIs and abstracts and returns an AbstractClassifier.

        acf_func = abstract_classifier_factory function
        """
        return self._create_classifier_factory().abstract_classifier_factory

    def _validate_api_key(self, validator: APIKeyValidator, api_key: str) -> None:
        if not validator.is_valid(api_key=api_key):
            raise ValueError(
                "Invalid API key. Please check your API key and try again."
            )

    def _make_files(self) -> None:
        if not os.listdir(INPUT_FILES_DIR_PATH):
            raise Exception(
                f"Input directory: {INPUT_FILES_DIR_PATH} contains no files to process."
            )

        files_to_split = [
            os.path.join(INPUT_FILES_DIR_PATH, file)
            for file in os.listdir(INPUT_FILES_DIR_PATH)
            if file.endswith(".json")
        ]

        for file_path in files_to_split:
            self.utilities.make_files(
                path_to_file=file_path,
                split_files_dir_path=SPLIT_FILES_DIR_PATH,
            )

        return self

    def _load_files(self) -> list[dict]:
        """Load all split files into a list of dictionaries."""
        data_list: list[dict] = []
        for file_name in os.listdir(SPLIT_FILES_DIR_PATH):
            file_path = os.path.join(SPLIT_FILES_DIR_PATH, file_name)
            if not os.path.isfile(file_path):
                continue

            try:
                with open(file_path, "r") as file:
                    data = json.load(file)
                    data_list.append(data)
            except Exception as e:
                self.warning_manager.log_warning(
                    "File Loading", f"Error loading file: {file_path}. Error: {e}"
                )

        return data_list


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    ai_api_key = os.getenv("OPENAI_API_KEY")
    pipeline_runner = PipelineRunner(ai_api_key=ai_api_key)
    pipeline_runner.run_pipeline()
