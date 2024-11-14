from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Union, Dict, List
import logging


from academic_metrics.dataclass_models import (
    CategoryInfo,
    FacultyStats,
)

from academic_metrics.constants import LOG_DIR_PATH

if TYPE_CHECKING:
    from academic_metrics.factories import (
        DataClassFactory,
        StrategyFactory,
        WarningManager,
        Utilities,
    )
    from academic_metrics.core import (
        FacultyPostprocessor,
        NameVariation,
        CategoryProcessor,
    )


class CategoryDataOrchestrator:
    """
    Orchestrates the processing of classified Crossref data into category statistics.

    This class handles the workflow of taking classified data and:
    1. Processing it through CategoryProcessor
    2. Managing faculty/department relationships
    3. Generating statistical outputs
    4. Serializing results to JSON files

    Attributes:
        data (list[dict]): Classified Crossref data to process
        output_dir_path (str): Path for storing output files
        extend (bool): Flag to determine if existing data should be extended
        strategy_factory (StrategyFactory): Factory for processing strategies
        warning_manager (WarningManager): Manager for warnings
        utils (Utilities): Utility object for helper functions
        category_processor (CategoryProcessor): Processor for category operations
        faculty_department_manager (FacultyDepartmentManager): Manager for faculty/department data
    """

    def __init__(
        self,
        *,
        data: list[dict],
        output_dir_path: str,
        category_processor: CategoryProcessor,
        faculty_postprocessor: FacultyPostprocessor,
        strategy_factory: StrategyFactory,
        dataclass_factory: DataClassFactory,
        warning_manager: WarningManager,
        utilities: Utilities,
        extend: bool = False,
    ):
        """
        Initializes the CategoryDataOrchestrator instance.

        Args:
            data (list[dict]): Classified Crossref data to process
            output_dir_path (str): Output directory path for results
            strategy_factory (StrategyFactory): Factory for processing strategies
            warning_manager (WarningManager): Warning management system
            utilities (Utilities): Utility functions
            extend (bool, optional): Whether to extend existing data. Defaults to False.

        Raises:
            AttributeError: If make_files is not a boolean.
            Exception: If make_files is True but the input directory is empty.

        Design:
            Sets up all necessary components for the processing pipeline.
            Initializes various managers and processors.
            Handles file splitting if required.
            Orchestrates the entire process including data refinement and serialization.

        Summary:
            Prepares and executes the complete workflow for processing academic publication data.
        """
        # Set up logger
        self.log_file_path = os.path.join(
            LOG_DIR_PATH, "category_data_orchestrator.log"
        )

        self.logger = logging.getLogger(__name__)
        self.logger.handlers = []
        self.logger.setLevel(logging.DEBUG)

        # Add handler if none exists
        if not self.logger.handlers:
            handler = logging.FileHandler(self.log_file_path)
            self.logger.setLevel(logging.DEBUG)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        self.data = data
        self.output_dir_path = output_dir_path
        self.extend = extend

        self.strategy_factory = strategy_factory
        self.warning_manager = warning_manager
        self.dataclass_factory = dataclass_factory
        self.utils = utilities

        # Initialize the CategoryProcessor and FacultyDepartmentManager with dependencies
        self.category_processor = category_processor

        # post-processor object
        self.faculty_postprocessor = faculty_postprocessor

    def run_orchestrator(self):
        self.category_processor.process_data_list(self.data)

        # category counts dict to pass to refine faculty sets
        category_data: dict[str, CategoryInfo] = (
            self.category_processor.get_category_data()
        )

        # Refine faculty sets to remove near duplicates and update counts
        self._refine_faculty_sets(
            faculty_postprocessor=self.faculty_postprocessor,
            category_dict=category_data,
        )
        self._refine_faculty_stats(
            faculty_stats=self.category_processor.faculty_stats,
            name_variations=self.faculty_postprocessor.name_variations,
            category_dict=category_data,
        )

        self._save_all_results()

    def _save_all_results(self):
        # Serialize the processed data and save it
        self._serialize_and_save_category_data(
            output_path=os.path.join(
                self.output_dir_path, "test_processed_category_data.json"
            ),
            category_data=self.category_processor.get_category_data(),
        )

        self._serialize_and_save_faculty_stats(
            output_path=os.path.join(
                self.output_dir_path, "test_processed_faculty_stats_data.json"
            ),
            faculty_stats=self.category_processor.get_faculty_stats(),
        )

        self._serialize_and_save_category_article_stats(
            output_path=os.path.join(
                self.output_dir_path, "test_processed_article_stats_data.json"
            ),
            article_stats=self.category_processor.get_category_article_stats(),
        )

        self._serialize_and_save_articles(
            output_path=os.path.join(
                self.output_dir_path, "test_processed_article_stats_obj_data.json"
            ),
            articles=self.category_processor.get_articles(),
        )

        self._serialize_and_save_global_faculty_stats(
            output_path=os.path.join(
                self.output_dir_path, "test_processed_global_faculty_stats_data.json"
            ),
            global_faculty_stats=self.category_processor.get_global_faculty_stats(),
        )

    @staticmethod
    def _refine_faculty_sets(
        faculty_postprocessor: FacultyPostprocessor,
        category_dict: dict[str, CategoryInfo],
    ):
        """
        Refines faculty sets by removing near duplicates and updating counts.

        Args:
            faculty_postprocessor (FacultyPostprocessor): Postprocessor for faculty data.
            faculty_department_manager (FacultyDepartmentManager): Manager for faculty and department data.
            category_dict (dict[str, CategoryInfo]): Dictionary of categories and their information.

        Design:
            Uses FacultyPostprocessor to remove near-duplicate faculty entries.
            Updates faculty and department counts after refinement.

        Summary:
            Improves the quality of faculty data by removing duplicates and updating related counts.
        """
        # Remove near duplicates
        faculty_postprocessor.remove_near_duplicates(category_dict=category_dict)

        # Update counts for each category
        for category, info in category_dict.items():
            info.set_params(
                {
                    "faculty_count": len(info.faculty),
                    "department_count": len(info.departments),
                }
            )

    def _refine_faculty_stats(
        self,
        *,
        faculty_stats: dict[str, FacultyStats],
        name_variations: dict[str, NameVariation],
        category_dict: dict[str, CategoryInfo],
    ):
        """
        Refines faculty statistics based on name variations.

        Args:
            faculty_stats (dict[str, FacultyStats]): Dictionary of faculty statistics.
            name_variations (dict[str, NameVariation]): Dictionary of name variations.
            category_dict (dict[str, CategoryInfo]): Dictionary of categories and their information.

        Design:
            Iterates through categories and faculty members.
            Applies refinement to faculty statistics based on name variations.

        Summary:
            Improves the accuracy of faculty statistics by accounting for name variations.
        """
        categories = list(category_dict.keys())
        for category in categories:
            # assigns faculty_stats dict from FacultyStats dataclass to category_faculty_stats
            category_faculty_stats = faculty_stats[category].faculty_stats

            faculty_members = list(faculty_stats[category].faculty_stats.keys())
            for faculty_member in faculty_members:
                faculty_stats[category].refine_faculty_stats(
                    faculty_name_unrefined=faculty_member,
                    name_variations=name_variations,
                )

    def _clean_category_data(self, category_data):
        """Prepare category data by removing unwanted keys"""
        # True: Exclude value(s) for key
        # False: Include value(s) for key
        exclude_keys_map = {
            "files": True,
            "faculty": False,
            "departments": False,
            "titles": False,
        }

        cleaned_data = {
            category: category_info.to_dict(
                # exclude keys is a list of strings matching keys in the dataclass to exclude
                # from the final dict when executing .to_dict()
                # We grab the key out and put that string in the list if it's value is True
                exclude_keys=[
                    key
                    for key, should_exclude in exclude_keys_map.items()
                    if should_exclude
                ]
            )
            for category, category_info in category_data.items()
        }
        return cleaned_data

    def _serialize_and_save_category_data(self, *, output_path, category_data):
        """Serialize and save category data"""
        # Step 1: Clean the data
        cleaned_data = self._clean_category_data(category_data)

        # Step 2: Convert to list of category info dicts
        flattened_data: List[Dict] = list(cleaned_data.values())

        # Step 3: Write to file
        self._write_to_json(flattened_data, output_path)

    def _serialize_and_save_faculty_stats(self, *, output_path, faculty_stats):
        """Serialize and save faculty stats"""
        # First .values() gets rid of the category level
        # Second .values() gets rid of the faculty_stats level
        # Third .values() gets rid of the faculty name level
        # We don't lose any data or need to insert it as we do so throughout the processing
        # By not only making them keys but also inserting them into the FacultyInfo objects
        # Define exclude keys map to parse into a list of keys to exclude from final dict
        exclude_keys_map = {
            "article_count": True,
            "average_citations": True,
            "doi_citation_map": True,
        }

        # List[FacultyInfo.to_dict()]
        flattened_data: List[Dict] = []

        # First level: Categories
        for category_stats in faculty_stats.values():
            # Second level: faculty_stats dict
            faculty_dict = category_stats.to_dict(
                # exclude keys is a list of strings matching keys in the dataclass to exclude
                # from the final dict when executing .to_dict()
                # We grab the key out and put that string in the list if it's value is True
                # True means exclude the value for that key
                exclude_keys=[
                    key
                    for key, should_exclude in exclude_keys_map.items()
                    if should_exclude
                ]
            )
            if "faculty_stats" in faculty_dict:  # Second level: faculty_stats dict
                # Third level: FacultyInfo obj
                for faculty_info_obj in faculty_dict["faculty_stats"].values():
                    # Convert FacultyInfo obj to dict and append to flattened_data
                    flattened_data.append(faculty_info_obj)
        self._write_to_json(flattened_data, output_path)

    def _serialize_and_save_global_faculty_stats(
        self, *, output_path, global_faculty_stats
    ):
        # Step 0: Define exclude keys map to parse into a list of keys to exclude from final dict
        exclude_keys_map = {
            "article_count": True,
            "average_citations": True,
            "citation_map": True,
        }

        # Step 1: Flatten and convert to list of dicts
        data: List[Dict] = [
            item.to_dict(
                exclude_keys=[
                    key
                    for key, should_exclude in exclude_keys_map.items()
                    if should_exclude
                ]
            )
            for item in global_faculty_stats.values()
        ]

        # Step 2: Write to file
        self._write_to_json(data, output_path)

    def _serialize_and_save_category_article_stats(self, *, output_path, article_stats):
        """Serialize and save category article stats"""
        flattened_data = []

        for category, stats in article_stats.items():
            stats_dict = stats.to_dict()
            if "article_citation_map" in stats_dict:
                for article in stats_dict["article_citation_map"].values():
                    flattened_data.append({**article})

        self._write_to_json(flattened_data, output_path)

    def _serialize_and_save_articles(self, *, output_path, articles):
        """Serialize and save the list of article objects from CategoryProcessor"""
        # Convert each CrossrefArticleDetails object to a dict
        article_dicts: List[Dict] = [article.to_dict() for article in articles]

        # Write to file
        self._write_to_json(article_dicts, output_path)

    def _flatten_to_list(self, data: Union[Dict, List]) -> List[Dict]:
        """Recursively flattens nested dictionaries/lists into a flat list of dictionaries.

        Args:
            data: Nested structure of dictionaries and lists

        Returns:
            List[Dict]: Flattened list of dictionaries

        Example:
            Input: {"cat1": {"article_map": {"doi1": {...}, "doi2": {...}}}}
            Output: [{...}, {...}]  # List of article dictionaries
        """
        flattened = []

        if isinstance(data, dict):
            for value in data.values():
                flattened.extend(self._flatten_to_list(value))
        elif isinstance(data, list):
            for item in data:
                flattened.extend(self._flatten_to_list(item))
        else:  # Base case: found a non-dict, non-list value
            if isinstance(data, dict):  # If it's a dictionary, add it
                flattened.append(data)

        return flattened

    def _write_to_json(self, data, output_path):
        """Write data to JSON file, handling extend mode"""
        if self.extend:
            with open(output_path, "r") as json_file:
                existing_data = json.load(json_file)
            if isinstance(data, list):
                existing_data.extend(data)
            else:
                existing_data.update(data)
            data = existing_data

        with open(output_path, "w") as json_file:
            json.dump(data, json_file, indent=4)


if __name__ == "__main__":
    raise NotImplementedError(
        "DEPRECATION NOTICE: Running CategoryDataOrchestrator directly is no longer supported. "
        "Please use the PipelineRunner class from academic_metrics/runners/pipeline.py as that is the new entry point. "
    )
