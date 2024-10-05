from utilities import Utilities
from My_Data_Classes import CategoryInfo
from generate_aux_stats import FacultyStats
from file_handler import FileHandler
from category_processor import CategoryProcessor
from faculty_department_manager import FacultyDepartmentManager
from faculty_set_postprocessor import FacultyPostprocessor, NameVariation
import os
import json
import re
import sys
from strategy_factory import StrategyFactory
from warning_manager import WarningManager

sys.path.append("/Users/spencerpresley/COSC425-MAIN/backend/PythonCode")
sys.path.append("/Users/spencerpresley/COSC425-MAIN/backend/GeneralUtilities")
from _AbstractCategoryMap import AbstractCategoryMap


class WosClassification:
    def __init__(
        self,
        *,
        input_dir_path: str,
        output_dir_path: str,
        strategy_factory: StrategyFactory,
        warning_manager: WarningManager,
        crossref_run: bool = False,
        make_files: bool = False
    ):
        """Handles entire orchestration of pipeline. Just create object and pass in directory_path as keyword argument."""
        self.input_dir_path = input_dir_path
        self.output_dir_path = output_dir_path

        self.strategy_factory = strategy_factory
        self.warning_manager = warning_manager
        self.utils = Utilities(
            strategy_factory=self.strategy_factory, warning_manager=self.warning_manager
        )

        if not isinstance(make_files, bool):
            raise AttributeError(f"Param: make_files value is {make_files} and is of type: {type(make_files)} for class: {self.__class__.__name__}. The make_files param must be of type: {type(bool)}.")

        elif make_files and not os.listdir(input_dir_path):
            raise Exception("Input directory: {input_dir_path} contains no files to process.")

        elif make_files:
            files_to_split = []
            for f in os.listdir(input_dir_path):
                files_to_split.append(os.path.join(input_dir_path, f))
            for f in files_to_split:
                self.utils.make_files(path_to_file=f, output_dir=output_dir_path, crossref_bool=crossref_run)

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
            output_dir_path=output_dir_path,
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
        self.serialize_and_save_data("test_processed_category_data.json")
        self.serialize_and_save_faculty_stats_data(
            "test_processed_faculty_stats_data.json"
        )
        self.serialize_and_save_article_stats_data(
            "test_processed_article_stats_data.json"
        )

        # AbstractCategoryMap(
        #     utilities_obj=self.utils,
        #     warning_manager=self.warning_manager,
        #     dir_path=self.directory_path,
        #     crossref_bool=crossref_run,
        # )

    def process_directory(self, *, output_dir_path, category_processor, crossref_bool):
        """
        Orchestrates the process of reading files from a directory,
        extracting categories, and updating faculty and department data.
        """
        # Use FileHandler to traverse the directory and process each file
        self.file_handler.construct_categories(
            directory_path=output_dir_path,
            category_processor=category_processor,
            warning_manager=self.warning_manager,
            crossref_bool=crossref_bool,
        )

    def get_category_counts(self):
        """
        Returns the current state of category counts dict
        """
        return self.category_processor.category_counts

    @staticmethod
    def refine_faculty_sets(
        faculty_postprocessor: FacultyPostprocessor,
        faculty_department_manager: FacultyDepartmentManager,
        category_dict: dict[str, CategoryInfo],
    ):
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

    def serialize_and_save_data(self, output_path="category_data.json"):
        """
        Serializes category data to JSON and saves it to a file.
        """
        self.addUrl()

        # Prepare category data for serialization using to_dict method from CategoryInfo class from My_Data_Classes.py
        categories_serializable = {
            category: category_info.to_dict()
            for category, category_info in self.get_category_counts().items()
        }

        for category, category_info in categories_serializable.items():
            del category_info["tc_list"]

        # Serialize to JSON and save to a file
        with open(output_path, "w") as json_file:
            json.dump(categories_serializable, json_file, indent=4)

        print(f"Data serialized and saved to {output_path}")

    def serialize_and_save_faculty_stats_data(
        self, output_path="faculty_stats_data.json"
    ):
        """
        Serializes faculty stats data to JSON and saves it to a file.
        """
        # Prepare faculty stats data for serialization using to_dict method from FacultyStats class from My_Data_Classes.py
        faculty_stats_serializable = {
            faculty_name: faculty_info.to_dict()
            for faculty_name, faculty_info in self.category_processor.faculty_stats.items()
        }

        # Serialize to JSON and save to a file
        with open(output_path, "w") as json_file:
            json.dump(faculty_stats_serializable, json_file, indent=4)

        self.warning_manager.log_warning(
            "Data Serialization",
            f"Faculty Stat Data serialized and saved to {output_path}",
        )

    def serialize_and_save_article_stats_data(
        self, output_path="article_stats_data.json"
    ):
        """
        Serializes article stats data to JSON and saves it to a file.
        """
        article_stats_serializable = {
            category: article_stats.to_dict()
            for category, article_stats in self.category_processor.article_stats.items()
        }

        # Serialize to JSON and save to a file
        with open(output_path, "w") as json_file:
            json.dump(article_stats_serializable, json_file, indent=4)

        self.warning_manager.log_warning(
            "Data Serialization",
            f"Article Stat Data serialized and saved to {output_path}",
        )


if __name__ == "__main__":
    # Define path to the directory containing the WoS txt files you want to process
    # directory_path = "./split_files"
    # directory_path = os.path.expanduser(directory_path)

    strategy_factory = StrategyFactory()
    warning_manager = WarningManager()

    input_dir_path = "./input_files"
    output_dir_path = "./crossref_split_files"
    input_dir_path = os.path.expanduser(input_dir_path)
    output_dir_path = os.path.expanduser(output_dir_path)
    
    # Instantiate the orchestrator class
    wos_classifiction = WosClassification(
        input_dir_path=input_dir_path,
        output_dir_path=output_dir_path,
        strategy_factory=strategy_factory,
        warning_manager=warning_manager,
        crossref_run=True,
        make_files=True
    )
    print("Processing complete.")
