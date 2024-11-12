from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

from academic_metrics.core import (
    FacultyPostprocessor,
    NameVariation,
    CategoryProcessor,
)

from academic_metrics.dataclass_models import (
    CategoryInfo,
    FacultyStats,
)

if TYPE_CHECKING:
    from academic_metrics.factories import (
        DataClassFactory,
        StrategyFactory,
        WarningManager,
        Utilities,
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
        self.data = data
        self.output_dir_path = output_dir_path
        self.extend = extend

        self.strategy_factory = strategy_factory
        self.warning_manager = warning_manager
        self.dataclass_factory = dataclass_factory
        self.utils = utilities

        # Initialize the CategoryProcessor and FacultyDepartmentManager with dependencies
        self.category_processor = CategoryProcessor(
            utils=self.utils,
            dataclass_factory=self.dataclass_factory,
            warning_manager=self.warning_manager,
        )

        # post-processor object
        self.faculty_postprocessor = FacultyPostprocessor()

    def run_orchestrator(self):
        self.category_processor.process_data_list(self.data)

        # category counts dict to pass to refine faculty sets
        category_data: dict[str, CategoryInfo] = self._get_category_data()

        # Refine faculty sets to remove near duplicates and update counts
        self.refine_faculty_sets(
            faculty_postprocessor=self.faculty_postprocessor,
            category_dict=category_data,
        )
        self.refine_faculty_stats(
            faculty_stats=self.category_processor.faculty_stats,
            name_variations=self.faculty_postprocessor.name_variations,
            category_dict=category_data,
        )

        self._save_all_results()

    def _save_all_results(self):
        # Serialize the processed data and save it
        self.serialize_and_save_data(
            output_path=os.path.join(
                self.output_dir_path, "test_processed_category_data.json"
            )
        )
        self.serialize_and_save_faculty_stats(
            output_path=os.path.join(
                self.output_dir_path, "test_processed_faculty_stats_data.json"
            )
        )

        self.serialize_and_save_article_stats(
            output_path=os.path.join(
                self.output_dir_path, "test_processed_article_stats_data.json"
            )
        )

        self.serialize_and_save_article_stats_obj(
            output_path=os.path.join(
                self.output_dir_path, "test_processed_article_stats_obj_data.json"
            )
        )
        self.serialize_and_save_global_faculty_stats(
            output_path=os.path.join(
                self.output_dir_path, "test_processed_global_faculty_stats_data.json"
            )
        )

    def _get_category_data(self):
        """
        Returns the current state of category counts dictionary.

        Returns:
            dict: A dictionary containing category counts.

        Design:
            Simply returns the category_data attribute from the category_processor.

        Summary:
            Provides access to the current state of category counts.
        """
        return self.category_processor.category_data

    @staticmethod
    def refine_faculty_sets(
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

    def refine_faculty_stats(
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
        cleaned_data = {
            category: category_info.to_dict(
                exclude_keys=["files", "faculty", "departments", "titles"]
            )
            for category, category_info in category_data.items()
        }
        return cleaned_data

    def _flatten_to_list(self, data_dict):
        """Convert dictionary of categories to flat list"""
        return list(data_dict.values())

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

    def serialize_and_save_data(self, *, output_path):
        """Serialize and save category data"""
        # Step 1: Clean the data
        cleaned_data = self._clean_category_data(self._get_category_data())

        # Step 2: Flatten to list
        flattened_data = self._flatten_to_list(cleaned_data)

        # Step 3: Write to file
        self._write_to_json(flattened_data, output_path)

    def serialize_and_save_faculty_stats(self, *, output_path):
        """Serialize and save faculty stats"""

        # Get all faculty stats as dicts
        data = {}
        for category, faculty_stats in self.category_processor.faculty_stats.items():
            data[category] = faculty_stats.to_dict()

        # Flatten into a single list of faculty info dicts
        flattened_data = []
        for category_dict in data.values():
            if category_dict:  # Only process non-empty dicts
                flattened_data.extend(category_dict.values())

        self._write_to_json(flattened_data, output_path)

    def serialize_and_save_article_stats(self, *, output_path):
        cleaned_data = {
            category: article_stats.to_dict()
            for category, article_stats in self.category_processor.article_stats.items()
        }

        flattened_data = self._flatten_to_list(cleaned_data)
        self._write_to_json(flattened_data, output_path)

    def serialize_and_save_article_stats_obj(self, *, output_path):
        """Serialize and save article stats object"""
        # Get the article stats dictionary directly
        article_stats_serializable = (
            self.category_processor.article_stats_obj.article_citation_map
        )

        # Convert each CrossrefArticleDetails object to a dict
        article_stats_to_save = {
            doi: details.to_dict()
            for doi, details in article_stats_serializable.items()
        }

        # Flatten to list of article details
        flattened_data = list(article_stats_to_save.values())

        # Write to file
        self._write_to_json(flattened_data, output_path)

    def serialize_and_save_global_faculty_stats(self, *, output_path):
        data = list(self.category_processor.global_faculty_stats.values())

        data = [item.to_dict() for item in data]

        # Step 2: Write to file
        self._write_to_json(data, output_path)


if __name__ == "__main__":
    raise NotImplementedError(
        "DEPRECATION NOTICE: Running CategoryDataOrchestrator directly is no longer supported. "
        "Please use the PipelineRunner class from academic_metrics/runners/pipeline.py as that is the new entry point. "
    )
