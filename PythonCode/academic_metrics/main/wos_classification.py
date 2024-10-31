import sys
import os

# print("Python version:", sys.version)
# print("sys.path:", sys.path)
# print("Current working directory:", os.getcwd())
# print("Contents of current directory:", os.listdir())

from academic_metrics.mapping import AbstractCategoryMap
from academic_metrics.strategies import StrategyFactory
from academic_metrics.utils import WarningManager, Utilities, FileHandler
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

# test
from academic_metrics.AI import AbstractClassifier
from academic_metrics.utils.taxonomy_util import Taxonomy
from academic_metrics.ChainBuilder import ChainManager
from academic_metrics.ai_prompts import (
    METHOD_JSON_FORMAT, 
    SENTENCE_ANALYSIS_JSON_EXAMPLE, 
    SUMMARY_JSON_STRUCTURE, 
    TAXONOMY_EXAMPLE, 
    CLASSIFICATION_SYSTEM_MESSAGE, 
    HUMAN_MESSAGE_PROMPT, 
    THEME_RECOGNITION_JSON_FORMAT, 
    THEME_RECOGNITION_SYSTEM_MESSAGE,
)

print("Imports successful")
continue_bool: bool = input("Continue? (y/n): ")
if continue_bool == "n":
    sys.exit()

import json
import re

# from academic_metrics.mapping import AbstractCategoryMap


class WosClassification:
    """
    Orchestrates the entire pipeline for processing and classifying Web of Science (WoS) or Crossref data.

    This class handles the complete workflow of reading input files, processing them,
    extracting relevant information, and generating output files with processed data.

    Attributes:
        input_dir_path (str): Path to the directory containing input files.
        split_files_dir_path (str): Path to the directory for storing split files.
        output_dir_path (str): Path to the directory for storing output files.
        extend (bool): Flag to determine if existing data should be extended.
        strategy_factory (StrategyFactory): Factory for creating various processing strategies.
        warning_manager (WarningManager): Manager for handling and logging warnings.
        utils (Utilities): Utility object for various helper functions.
        category_processor (CategoryProcessor): Processor for handling category-related operations.
        faculty_department_manager (FacultyDepartmentManager): Manager for faculty and department data.
        file_handler (FileHandler): Handler for file operations.

    Methods:
        process_directory: Orchestrates the processing of files in the specified directory.
        get_category_counts: Retrieves the current state of category counts.
        refine_faculty_sets: Refines faculty sets by removing near duplicates and updating counts.
        refine_faculty_stats: Refines faculty statistics based on name variations.
        addUrl: Adds URL-friendly versions of category names.
        serialize_and_save_data: Serializes and saves category data to a JSON file.
        serialize_and_save_faculty_stats_data: Serializes and saves faculty statistics to a JSON file.
        serialize_and_save_article_stats_data: Serializes and saves article statistics to a JSON file.
        convert_sets_to_lists: Converts sets to lists in a dictionary recursively.

    Design:
        Implements a comprehensive pipeline for processing academic publication data.
        Utilizes various helper classes and methods for specific tasks in the pipeline.
        Handles both WoS and Crossref data formats.

    Summary:
        Provides a high-level interface for processing academic publication data,
        including categorization, faculty and department management, and data serialization.
    """

    def __init__(
        self,
        *,
        input_dir_path: str,
        split_files_dir_path: str,
        output_dir_path: str,
        strategy_factory: StrategyFactory,
        warning_manager: WarningManager,
        crossref_run: bool = False,
        make_files: bool = False,
        extend: bool = False,
    ):
        """
        Initializes the WosClassification instance and sets up the processing pipeline.

        Args:
            input_dir_path (str): Path to the directory containing input files.
            split_files_dir_path (str): Path to the directory for storing split files.
            output_dir_path (str): Path to the directory for storing output files.
            strategy_factory (StrategyFactory): Factory for creating various processing strategies.
            warning_manager (WarningManager): Manager for handling and logging warnings.
            crossref_run (bool, optional): Flag to indicate if processing Crossref data. Defaults to False.
            make_files (bool, optional): Flag to indicate if new files should be created. Defaults to False.
            extend (bool, optional): Flag to determine if existing data should be extended. Defaults to False.

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
        self.input_dir_path = input_dir_path
        self.split_files_dir_path = split_files_dir_path
        self.output_dir_path = output_dir_path
        self.extend = extend

        self.strategy_factory = strategy_factory
        self.warning_manager = warning_manager
        self.utils = Utilities(
            strategy_factory=self.strategy_factory, warning_manager=self.warning_manager
        )

        if not isinstance(make_files, bool):
            raise AttributeError(
                f"Param: make_files value is {make_files} and is of type: {type(make_files)} for class: {self.__class__.__name__}. The make_files param must be of type: {type(bool)}."
            )

        elif make_files and not os.listdir(input_dir_path):
            raise Exception(
                "Input directory: {input_dir_path} contains no files to process."
            )

        elif make_files:
            files_to_split = []
            for f in os.listdir(input_dir_path):
                files_to_split.append(os.path.join(input_dir_path, f))
            for f in files_to_split:
                self.utils.make_files(
                    path_to_file=f,
                    split_files_dir_path=split_files_dir_path,
                    crossref_bool=crossref_run,
                )

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

        self.file_handler = FileHandler(self.utils)

        self.process_directory(
            split_files_dir_path=split_files_dir_path,
            category_processor=self.category_processor,
            crossref_bool=crossref_run,
        )

        # post-processor object
        faculty_postprocessor = FacultyPostprocessor()

        # category counts dict to pass to refine faculty sets
        category_counts: dict[str, CategoryInfo] = self.get_category_counts()

        # Refine faculty sets to remove near duplicates and update counts
        self.refine_faculty_sets(
            faculty_postprocessor, self.faculty_department_manager, category_counts
        )
        self.refine_faculty_stats(
            faculty_stats=self.category_processor.faculty_stats,
            name_variations=faculty_postprocessor.name_variations,
            category_dict=category_counts,
        )

        # Serialize the processed data and save it
        self.serialize_and_save_data(
            output_path=os.path.join(
                output_dir_path, "test_processed_category_data.json"
            )
        )
        self.serialize_and_save_faculty_stats_data(
            output_path=os.path.join(
                output_dir_path, "test_processed_faculty_stats_data.json"
            )
        )
        self.serialize_and_save_article_stats_data(
            output_path=os.path.join(
                output_dir_path, "test_processed_article_stats_data.json"
            )
        )
        self.serialize_and_save_article_stats_obj(
            output_path=os.path.join(
                output_dir_path, "test_processed_article_stats_obj_data.json"
            )
        )
        
        self.serialize_and_save_crossref_article_stats(
            output_path=os.path.join(
                output_dir_path, "test_processed_crossref_article_stats_data.json"
            )
        )
        
        self.serialize_and_save_crossref_article_stats_obj(
            output_path=os.path.join(
                output_dir_path, "test_processed_crossref_article_stats_obj_data.json"
            )
        )

        # AbstractCategoryMap(
        #     utilities_obj=self.utils,
        #     warning_manager=self.warning_manager,
        #     dir_path=self.directory_path,
        #     crossref_bool=crossref_run,
        # )

    def process_directory(
        self, *, split_files_dir_path, category_processor, crossref_bool
    ):
        """
        Orchestrates the process of reading files from a directory,
        extracting categories, and updating faculty and department data.

        Args:
            split_files_dir_path (str): Path to the directory containing split files.
            category_processor (CategoryProcessor): Processor for handling category-related operations.
            crossref_bool (bool): Flag indicating if processing Crossref data.

        Design:
            Uses FileHandler to traverse the directory and process each file.
            Updates category, faculty, and department data based on file contents.

        Summary:
            Processes all files in the specified directory to extract and update relevant data.
        """
        # Use FileHandler to traverse the directory and process each file
        self.file_handler.construct_categories(
            directory_path=split_files_dir_path,
            category_processor=category_processor,
            warning_manager=self.warning_manager,
            crossref_bool=crossref_bool,
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
                category_info.to_dict(exclude_keys=["files", "faculty", "departments", "titles"])
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

    def serialize_and_save_faculty_stats_data(self, *, output_path):
        """
        Serializes faculty stats data to JSON and saves it to a file.

        Args:
            output_path (str): Path to save the serialized data.

        Design:
            Prepares faculty statistics data for serialization.
            Handles extending existing data if required.
            Serializes and saves data to a JSON file.

        Summary:
            Saves processed faculty statistics in a JSON format for further use or analysis.
        """
        # Prepare faculty stats data for serialization using to_dict method from FacultyStats class from My_Data_Classes.py
        faculty_stats_serializable = {
            faculty_name: self.convert_sets_to_lists(faculty_info.to_dict())
            for faculty_name, faculty_info in self.category_processor.faculty_stats.items()
        }

        # Read and update existing data if extending
        if self.extend:
            with open(output_path, "r") as json_file:
                existing_data = json.load(json_file)
            existing_data.update(faculty_stats_serializable)
            faculty_stats_serializable = existing_data

        # Serialize to JSON and save to a file
        with open(output_path, "w") as json_file:
            json.dump(faculty_stats_serializable, json_file, indent=4)

        self.warning_manager.log_warning(
            "Data Serialization",
            f"Faculty Stat Data serialized and saved to {output_path}",
        )

    def serialize_and_save_article_stats_data(self, *, output_path):
        """
        Serializes article stats data to JSON and saves it to a file.

        Args:
            output_path (str): Path to save the serialized data.

        Design:
            Prepares article statistics data for serialization.
            Handles extending existing data if required.
            Serializes and saves data to a JSON file.

        Summary:
            Saves processed article statistics in a JSON format for further use or analysis.
        """
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
            f"Article Stat Data serialized and saved to {output_path}",
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
            f"Article Stat Data serialized and saved to {output_path}",
        )
        
    def serialize_and_save_crossref_article_stats(self, *, output_path):
        crossref_article_stats_serializable = {
            category: self.convert_sets_to_lists(article_stats.to_dict())
            for category, article_stats in self.category_processor.crossref_article_stats.items()
        }
        
        # Read and update existing data if extending
        if self.extend:
            with open(output_path, "r") as json_file:
                existing_data = json.load(json_file)
            existing_data.update(article_stats_serializable)
            article_stats_serializable = existing_data

        # Serialize to JSON and save to a file
        with open(output_path, "w") as json_file:
            json.dump(crossref_article_stats_serializable, json_file, indent=4)

        self.warning_manager.log_warning(
            "Data Serialization",
            f"Crossref Article Stat Data serialized and saved to {output_path}",
        )
          
    def serialize_and_save_crossref_article_stats_obj(self, *, output_path):
        article_stats_serializable = self.category_processor.crossref_article_stats_obj.to_dict()
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
    # Define path to the directory containing the WoS txt files you want to process
    # directory_path = "./split_files"
    # directory_path = os.path.expanduser(directory_path)
    print("testing imports")
    strategy_factory = StrategyFactory()
    warning_manager = WarningManager()

    this_directory = os.path.dirname(os.path.abspath(__file__))
    data_core_dir = os.path.join(this_directory, "..", "..", "data", "core")
    input_dir_path = os.path.join(data_core_dir, "input_files")
    split_files_dir_path = os.path.join(data_core_dir, "crossref_split_files")
    input_dir_full_path = os.path.expanduser(input_dir_path)
    split_files_dir_full_path = os.path.expanduser(split_files_dir_path)
    output_dir_path = os.path.join(data_core_dir, "output_files")
    output_dir_full_path = os.path.expanduser(output_dir_path)
    # Instantiate the orchestrator class
    wos_classifiction = WosClassification(
        input_dir_path=input_dir_full_path,
        split_files_dir_path=split_files_dir_full_path,
        output_dir_path=output_dir_full_path,
        strategy_factory=strategy_factory,
        warning_manager=warning_manager,
        crossref_run=True,
        make_files=True,
        extend=False,
    )
    print("Processing complete.")
