import sys
import os

# print("Python version:", sys.version)
# print("sys.path:", sys.path)
# print("Current working directory:", os.getcwd())
# print("Contents of current directory:", os.listdir())

from academic_metrics.mapping import AbstractCategoryMap
from academic_metrics.strategies import StrategyFactory
from academic_metrics.utils import (
    WarningManager,
    Utilities,
)
from academic_metrics.utils.taxonomy_util import Taxonomy
from academic_metrics.core import (
    FacultyDepartmentManager,
    FacultyPostprocessor,
    NameVariation,
    CategoryProcessor,
)
from academic_metrics.data_models import (
    CategoryInfo,
    FacultyStats,
)
from urllib.parse import quote
import shortuuid

import json
import re


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
        self.utils = utilities

        # Initialize the CategoryProcessor and FacultyDepartmentManager with dependencies
        self.category_processor = CategoryProcessor(
            self.utils, None, self.warning_manager
        )

        # Intialize FacultyDepartmentManager
        self.faculty_department_manager = FacultyDepartmentManager(
            self.category_processor
        )

        # Link CategoryProcessor and FacultyDepartmentManager
        self.category_processor.faculty_department_manager = (
            self.faculty_department_manager
        )

        # post-processor object
        self.faculty_postprocessor = FacultyPostprocessor()

    def run_orchestrator(self):
        self.category_processor.process_data_list(self.data)

        # category counts dict to pass to refine faculty sets
        category_counts: dict[str, CategoryInfo] = self.get_category_counts()

        # Refine faculty sets to remove near duplicates and update counts
        self.refine_faculty_sets(
            faculty_postprocessor=self.faculty_postprocessor,
            faculty_department_manager=self.faculty_department_manager,
            category_dict=category_counts,
        )
        self.refine_faculty_stats(
            faculty_stats=self.category_processor.faculty_stats,
            name_variations=self.faculty_postprocessor.name_variations,
            category_dict=category_counts,
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

    def get_category_counts(self):
        """
        Returns the current state of category counts dictionary.

        Returns:
            dict: A dictionary containing category counts.

        Design:
            Simply returns the category_counts attribute from the category_processor.

        Summary:
            Provides access to the current state of category counts.
        """
        return self.category_processor.category_counts

    @staticmethod
    def refine_faculty_sets(
        faculty_postprocessor: FacultyPostprocessor,
        faculty_department_manager: FacultyDepartmentManager,
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
        faculty_postprocessor.remove_near_duplicates(category_dict=category_dict)
        faculty_department_manager.update_faculty_count()
        faculty_department_manager.update_department_count()

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

    def addUrl(self):
        """
        Adds URL-friendly versions of category names to the category data.

        Design:
            Converts category names to URL-friendly format.
            Updates the category information with the URL-friendly version.

        Summary:
            Enhances category data with URL-friendly names for web applications.
        """
        tempDict = self.get_category_counts()
        # This pattern now matches characters not allowed in a URL
        pattern = re.compile(r"[^A-Za-z0-9-]+")
        for category, values in tempDict.items():
            # Replace matched characters with a hyphen
            url = pattern.sub("-", category.lower())
            # Remove potential multiple hyphens with a single one
            url = re.sub("-+", "-", url)
            # Remove leading or trailing hyphens
            url = url.strip("-")
            values.url = url

    def generate_short_uuid_as_url(self, article_stats_to_save):
        for title, article_details in article_stats_to_save.items():
            article_details["url"] = shortuuid.uuid(title)

    def serialize_and_save_data(self, *, output_path):
        """
        Serializes category data to JSON and saves it to a file.

        Args:
            output_path (str): Path to save the serialized data.

        Design:
            Prepares category data for serialization.
            Handles extending existing data if required.
            Serializes and saves data to a JSON file.

        Summary:
            Saves processed category data in a JSON format for further use or analysis.
        """
        self.addUrl()

        # Prepare category data for serialization using to_dict method from CategoryInfo class from My_Data_Classes.py
        categories_serializable = {
            category: self.convert_sets_to_lists(
                category_info.to_dict(
                    exclude_keys=["files", "faculty", "departments", "titles"]
                )
            )
            for category, category_info in self.get_category_counts().items()
        }

        for category, category_info in categories_serializable.items():
            del category_info["tc_list"]

        # Read existing data if extending
        if self.extend:
            with open(output_path, "r") as json_file:
                existing_data = json.load(json_file)
            existing_data.update(categories_serializable)
            categories_serializable = existing_data

        # Serialize to JSON and save to a file
        with open(output_path, "w") as json_file:
            json.dump(categories_serializable, json_file, indent=4)

        print(f"Data serialized and saved to {output_path}")

    def serialize_and_save_faculty_stats(self, *, output_path):
        faculty_stats_serializable = {
            category: self.convert_sets_to_lists(faculty_stats.to_dict())
            for category, faculty_stats in self.category_processor.faculty_stats.items()
        }

        if self.extend:
            with open(output_path, "r") as json_file:
                existing_data = json.load(json_file)
            existing_data.update(faculty_stats_serializable)
            faculty_stats_serializable = existing_data

        with open(output_path, "w") as json_file:
            json.dump(faculty_stats_serializable, json_file, indent=4)

    def serialize_and_save_article_stats(self, *, output_path):
        article_stats_serializable = {
            category: self.convert_sets_to_lists(article_stats.to_dict())
            for category, article_stats in self.category_processor.article_stats.items()
        }

        # Read and update existing data if extending
        if self.extend:
            with open(output_path, "r") as json_file:
                existing_data = json.load(json_file)
            existing_data.update(article_stats_serializable)
            article_stats_serializable = existing_data

        # Serialize to JSON and save to a file
        with open(output_path, "w") as json_file:
            json.dump(article_stats_serializable, json_file, indent=4)

        self.warning_manager.log_warning(
            "Data Serialization",
            f"Crossref Article Stat Data serialized and saved to {output_path}",
        )

    def serialize_and_save_article_stats_obj(self, *, output_path):
        article_stats_serializable = self.category_processor.article_stats_obj.to_dict()
        article_stats_to_save = article_stats_serializable["article_citation_map"]

        self.generate_short_uuid_as_url(article_stats_to_save)

        if self.extend:
            with open(output_path, "r") as json_file:
                existing_data = json.load(json_file)
            existing_data.update(article_stats_to_save)
            article_stats_to_save = existing_data

        with open(output_path, "w") as json_file:
            json.dump(article_stats_to_save, json_file, indent=4)

        self.warning_manager.log_warning(
            "Data Serialization",
            f"Crossref Article Stat Data serialized and saved to {output_path}",
        )

    def convert_sets_to_lists(self, data_dict):
        """
        Recursively converts sets to lists in a dictionary.

        Args:
            data_dict (dict): The dictionary to process.

        Returns:
            dict: The processed dictionary with sets converted to lists.

        Design:
            Recursively traverses the dictionary.
            Converts set objects to list objects.
            Handles nested dictionaries.

        Summary:
            Ensures all set objects in the dictionary are converted to lists for JSON serialization.
        """
        for key, value in data_dict.items():
            if isinstance(value, set):
                data_dict[key] = list(value)
            elif isinstance(value, dict):
                data_dict[key] = self.convert_sets_to_lists(value)
        return data_dict


if __name__ == "__main__":
    raise NotImplementedError(
        "DEPRECATION NOTICE: Running CategoryDataOrchestrator directly is no longer supported. "
        "Please use the PipelineRunner class from academic_metrics/runners/pipeline.py as that is the new entry point. "
    )
