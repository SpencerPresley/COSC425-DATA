from __future__ import annotations

import json
import logging
import os
from typing import TYPE_CHECKING, Dict, List, Union

from academic_metrics.configs import (
    configure_logging,
    DEBUG,
)
from academic_metrics.dataclass_models import CategoryInfo, FacultyStats

if TYPE_CHECKING:
    from academic_metrics.core import (
        CategoryProcessor,
        FacultyPostprocessor,
        NameVariation,
    )
    from academic_metrics.dataclass_models import (
        CrossrefArticleDetails,
        CrossrefArticleStats,
    )
    from academic_metrics.factories import (
        DataClassFactory,
        StrategyFactory,
        Utilities,
        WarningManager,
    )


class CategoryDataOrchestrator:
    """Orchestrates the processing and organization of academic publication data.

    This class manages the workflow of processing classified publication data through various stages:
    1. Processing raw data through CategoryProcessor
    2. Managing faculty/department relationships
    3. Generating statistical outputs
    4. Serializing results to JSON files

    Attributes:
        data (List[Dict]): Raw classified publication data to process.
        output_dir_path (str): Directory path for output files.
        extend (bool): Whether to extend existing data files.
        strategy_factory (StrategyFactory): Factory for creating processing strategies.
        warning_manager (WarningManager): System for handling and logging warnings.
        dataclass_factory (DataClassFactory): Factory for creating data model instances.
        utils (Utilities): General utility functions.
        category_processor (CategoryProcessor): Processor for category-related operations.
        faculty_postprocessor (FacultyPostprocessor): Processor for faculty data refinement.
        final_category_data (List[Dict]): Processed category statistics.
        final_faculty_data (List[Dict]): Processed faculty statistics.
        final_article_stats_data (List[Dict]): Processed article statistics.
        final_article_data (List[Dict]): Processed article details.
        final_global_faculty_data (List[Dict]): Processed global faculty statistics.
        logger (logging.Logger): Logger instance for this class.
        log_file_path (str): Path to the log file.

    Public Methods:
        run_orchestrator: Executes the main data processing workflow.
        get_final_category_data: Returns processed category data.
        get_final_faculty_data: Returns processed faculty data.
        get_final_global_faculty_data: Returns processed global faculty data.
        get_final_article_stats_data: Returns processed article statistics.
        get_final_article_data: Returns processed article details.

    Private Methods:
        _save_all_results: Saves all processed data to files.
        _refine_faculty_sets: Refines faculty sets by removing duplicates.
        _refine_faculty_stats: Refines faculty statistics based on name variations.
        _clean_category_data: Prepares category data by removing unwanted keys.
        _serialize_and_save_category_data: Serializes and saves category data.
        _serialize_and_save_faculty_stats: Serializes and saves faculty statistics.
        _serialize_and_save_global_faculty_stats: Serializes and saves global faculty statistics.
        _serialize_and_save_category_article_stats: Serializes and saves article statistics.
        _serialize_and_save_articles: Serializes and saves article details.
        _flatten_to_list: Flattens nested data structures into a list.
        _write_to_json: Writes data to JSON file.
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
    ) -> None:
        """Initialize the CategoryDataOrchestrator with required components and settings.

        Sets up logging configuration with both file and console handlers and
        initializes internal data structures for storing processed results.

        Args:
            data (list[dict]): Raw classified publication data to process.
            output_dir_path (str): Directory path where output files will be saved.
            category_processor (CategoryProcessor): Processor for handling category-related operations.
            faculty_postprocessor (FacultyPostprocessor): Processor for faculty data refinement.
            strategy_factory (StrategyFactory): Factory for creating processing strategies.
            dataclass_factory (DataClassFactory): Factory for creating data model instances.
            warning_manager (WarningManager): System for handling and logging warnings.
            utilities (Utilities): General utility functions.
            extend (bool, optional): Whether to extend existing data files. Defaults to False.

        Raises:
            ValueError: If output directory path doesn't exist or isn't writable.
            TypeError: If any of the processor or factory arguments are of incorrect type.
        """
        self.logger = configure_logging(
            module_name=__name__,
            log_file_name="category_data_orchestrator",
            log_level=DEBUG,
        )

        self.logger.info("Initializing CategoryDataOrchestrator...")
        self.logger.info(f"Data: {data}")
        self.logger.info(f"Output directory path: {output_dir_path}")
        self.logger.info(f"Extend: {extend}")

        self.data: List[Dict] = data
        self.output_dir_path: str = output_dir_path
        self.extend: bool = extend

        self.logger.info("Assigning strategy factory...")
        self.strategy_factory = strategy_factory
        self.logger.info("Strategy factory assigned.")

        self.logger.info("Assigning warning manager...")
        self.warning_manager: WarningManager = warning_manager
        self.logger.info("Warning manager assigned.")

        self.logger.info("Assigning dataclass factory...")
        self.dataclass_factory: DataClassFactory = dataclass_factory
        self.logger.info("Dataclass factory assigned.")

        self.logger.info("Assigning utilities...")
        self.utils: Utilities = utilities
        self.logger.info("Utilities assigned.")

        # Initialize the CategoryProcessor and FacultyDepartmentManager with dependencies
        self.logger.info("Assigning category processor...")
        self.category_processor: CategoryProcessor = category_processor
        self.logger.info("Category processor assigned.")

        # post-processor object
        self.logger.info("Assigning faculty postprocessor...")
        self.faculty_postprocessor: FacultyPostprocessor = faculty_postprocessor
        self.logger.info("Faculty postprocessor assigned.")

        self.logger.info("Initializing final data structures...")
        self.final_category_data: List[Dict] = []
        self.final_faculty_data: List[Dict] = []
        self.final_article_stats_data: List[Dict] = []
        self.final_article_data: List[Dict] = []
        self.final_global_faculty_data: List[Dict] = []
        self.logger.info("Final data structures initialized.")

    def run_orchestrator(self) -> None:
        """Execute the main data processing workflow.

        Processes the raw publication data through several stages:
        1. Processes data through CategoryProcessor
        2. Gets category data for faculty set refinement
        3. Refines faculty sets to remove duplicates
        4. Refines faculty statistics with name variations
        5. Saves all processed results to files

        Raises:
            ValueError: If category data processing fails.
            IOError: If saving results to files fails.
        """
        self.logger.info("Processing data through category processor...")
        self.category_processor.process_data_list(self.data)
        self.logger.info("Data processed through category processor.")

        # category counts dict to pass to refine faculty sets
        self.logger.info("Getting category data...")
        category_data: dict[str, CategoryInfo] = (
            self.category_processor.get_category_data()
        )
        self.logger.info("Category data retrieved.")

        # Refine faculty sets to remove near duplicates and update counts
        self.logger.info(
            "Refining faculty sets to remove near duplicates and update counts..."
        )
        self._refine_faculty_sets(
            faculty_postprocessor=self.faculty_postprocessor,
            category_dict=category_data,
        )
        self.logger.info("Faculty sets refined.")

        self.logger.info("Refining faculty statistics with name variations...")
        self._refine_faculty_stats(
            faculty_stats=self.category_processor.faculty_stats,
            name_variations=self.faculty_postprocessor.name_variations,
            category_dict=category_data,
        )
        self.logger.info("Faculty statistics refined.")

        self.logger.info("Saving all processed results to files...")
        self._save_all_results()
        self.logger.info("All processed results saved to files.")

    def get_final_category_data(self) -> List[Dict]:
        """Retrieve the processed category data.

        Returns:
            List[Dict]: List of processed category data dictionaries.

        Raises:
            ValueError: If final category data hasn't been generated yet.
        """
        self.logger.info("Getting final category data...")
        if not hasattr(self, "final_category_data"):
            self.logger.error("Final category data not yet generated")
            raise ValueError("Final category data not yet generated")
        self.logger.info("Final category data retrieved.")
        return self.final_category_data

    def get_final_faculty_data(self) -> List[Dict]:
        """Retrieve the processed faculty data.

        Returns:
            List[Dict]: List of processed faculty data dictionaries.

        Raises:
            ValueError: If final faculty data hasn't been generated yet.
        """
        self.logger.info("Getting final faculty data...")
        if not hasattr(self, "final_faculty_data"):
            self.logger.error("Final faculty data not yet generated")
            raise ValueError("Final faculty data not yet generated")
        self.logger.info("Final faculty data retrieved.")
        return self.final_faculty_data

    def get_final_global_faculty_data(self) -> List[Dict]:
        """Retrieve the processed global faculty data.

        Returns:
            List[Dict]: List of processed global faculty data dictionaries.

        Raises:
            ValueError: If final global faculty data hasn't been generated yet.
        """
        self.logger.info("Getting final global faculty data...")
        if not hasattr(self, "final_global_faculty_data"):
            self.logger.error("Final global faculty data not yet generated")
            raise ValueError("Final global faculty data not yet generated")
        self.logger.info("Final global faculty data retrieved.")
        return self.final_global_faculty_data

    def get_final_article_stats_data(self) -> List[Dict]:
        """Retrieve the processed article statistics data.

        Returns:
            List[Dict]: List of processed article statistics dictionaries.

        Raises:
            ValueError: If final article statistics data hasn't been generated yet.
        """
        self.logger.info("Getting final article stats data...")
        if not hasattr(self, "final_article_stats_data"):
            self.logger.error("Final article stats data not yet generated")
            raise ValueError("Final article stats data not yet generated")
        self.logger.info("Final article stats data retrieved.")
        return self.final_article_stats_data

    def get_final_article_data(self) -> List[Dict]:
        """Retrieve the processed article data.

        Returns:
            List[Dict]: List of processed article data dictionaries.

        Raises:
            ValueError: If final article data hasn't been generated yet.
        """
        self.logger.info("Getting final article data...")
        if not hasattr(self, "final_article_data"):
            self.logger.error("Final article data not yet generated")
            raise ValueError("Final article data not yet generated")
        self.logger.info("Final article data retrieved.")
        return self.final_article_data

    def _save_all_results(self) -> None:
        """Save all processed data to their respective JSON files.

        Serializes and saves:
        1. Category data
        2. Faculty statistics
        3. Article statistics
        4. Article details
        5. Global faculty statistics

        Raises:
            IOError: If any file operations fail.
        """
        self.logger.info("Serializing and saving category data...")

        # Serialize the processed data and save it
        self.logger.info("Serializing and saving category data...")
        self._serialize_and_save_category_data(
            output_path=os.path.join(
                self.output_dir_path, "test_processed_category_data.json"
            ),
            category_data=self.category_processor.get_category_data(),
        )
        self.logger.info("Category data serialized and saved.")

        self.logger.info("Serializing and saving faculty stats...")
        self._serialize_and_save_faculty_stats(
            output_path=os.path.join(
                self.output_dir_path, "test_processed_faculty_stats_data.json"
            ),
            faculty_stats=self.category_processor.get_faculty_stats(),
        )
        self.logger.info("Faculty stats serialized and saved.")

        self.logger.info("Serializing and saving article stats...")
        self._serialize_and_save_category_article_stats(
            output_path=os.path.join(
                self.output_dir_path, "test_processed_article_stats_data.json"
            ),
            article_stats=self.category_processor.get_category_article_stats(),
        )
        self.logger.info("Article stats serialized and saved.")

        self.logger.info("Serializing and saving articles...")
        self._serialize_and_save_articles(
            output_path=os.path.join(
                self.output_dir_path, "test_processed_article_stats_obj_data.json"
            ),
            articles=self.category_processor.get_articles(),
        )
        self.logger.info("Articles serialized and saved.")

        self.logger.info("Serializing and saving global faculty stats...")
        self._serialize_and_save_global_faculty_stats(
            output_path=os.path.join(
                self.output_dir_path, "test_processed_global_faculty_stats_data.json"
            ),
            global_faculty_stats=self.category_processor.get_global_faculty_stats(),
        )
        self.logger.info("Global faculty stats serialized and saved.")

    @staticmethod
    def _refine_faculty_sets(
        faculty_postprocessor: FacultyPostprocessor,
        category_dict: dict[str, CategoryInfo],
    ) -> None:
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
        for _, info in category_dict.items():
            info.set_params(
                {
                    "faculty_count": len(info.faculty),
                    "department_count": len(info.departments),
                }
            )

    def _refine_faculty_stats(
        self,
        *,
        faculty_stats: Dict[str, FacultyStats],
        name_variations: Dict[str, NameVariation],
        category_dict: Dict[str, CategoryInfo],
    ) -> None:
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
        self.logger.info("Refining faculty statistics with name variations...")
        self.logger.info("Grabbing category_dict keys...")
        categories: List[str] = list(category_dict.keys())
        self.logger.info(f"Grabbed category_dict keys: {categories}")

        self.logger.info("Iterating through categories...")
        for category in categories:
            self.logger.info(f"Processing category: {category}")
            # assigns faculty_stats dict from FacultyStats dataclass to category_faculty_stats
            # category_faculty_stats: Dict[str, FacultyInfo] = faculty_stats[
            #     category
            # ].faculty_stats

            self.logger.info("Grabbing faculty members...")
            faculty_members: List[str] = list(
                faculty_stats[category].faculty_stats.keys()
            )
            self.logger.info(f"Grabbed faculty members: {faculty_members}")

            self.logger.info("Refining faculty stats...")
            for faculty_member in faculty_members:
                faculty_stats[category].refine_faculty_stats(
                    faculty_name_unrefined=faculty_member,
                    name_variations=name_variations,
                )
            self.logger.info("Faculty stats refined.")

    def _clean_category_data(
        self, category_data: Dict[str, CategoryInfo]
    ) -> Dict[str, Dict]:
        """Prepare category data by removing unwanted keys.

        Args:
            category_data (Dict[str, CategoryInfo]): Raw category data to clean.

        Returns:
            Dict[str, Dict]: Cleaned category data with specified keys removed.
        """
        self.logger.info("Cleaning category data...")
        # True: Exclude value(s) for key
        # False: Include value(s) for key
        self.logger.info("Defining exclude keys map...")
        exclude_keys_map = {
            "files": True,
            "faculty": False,
            "departments": False,
            "titles": False,
        }
        self.logger.info(f"Exclude keys map: {exclude_keys_map}")

        self.logger.info("Iterating through categories...")
        cleaned_data: Dict[str, Dict] = {
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
        self.logger.info("Category data cleaned.")
        return cleaned_data

    def _serialize_and_save_category_data(
        self, *, output_path: str, category_data: Dict[str, Dict]
    ) -> None:
        """Serialize and save category data to JSON file.

        Args:
            output_path (str): Path where the JSON file will be saved.
            category_data (Dict[str, Dict]): Category data to serialize.

        Raises:
            IOError: If file writing fails.
        """
        self.logger.info("Cleaning category data...")
        # Step 1: Clean the data
        cleaned_data: Dict[str, Dict] = self._clean_category_data(category_data)
        self.logger.info("Category data cleaned.")

        # Step 2: Convert to list of category info dicts
        self.logger.info("Converting to list of category info dicts...")
        flattened_data: List[Dict] = list(cleaned_data.values())
        self.logger.info(f"Flattened data: {flattened_data}")

        self.logger.info("Assigning flattened data to final_category_data...")
        self.final_category_data = flattened_data
        self.logger.info("Final category data assigned.")

        self.logger.info("Writing to file...")
        # Step 3: Write to file
        self._write_to_json(flattened_data, output_path)

    def _serialize_and_save_faculty_stats(
        self, *, output_path: str, faculty_stats: Dict[str, FacultyStats]
    ) -> None:
        """Serialize and save faculty statistics to JSON file.

        Args:
            output_path (str): Path where the JSON file will be saved.
            faculty_stats (Dict[str, FacultyStats]): Faculty statistics to serialize.

        Raises:
            IOError: If file writing fails.
        """
        self.logger.info("Serializing and saving faculty stats...")

        # First .values() gets rid of the category level
        # Second .values() gets rid of the faculty_stats level
        # Third .values() gets rid of the faculty name level
        # We don't lose any data or need to insert it as we do so throughout the processing
        # By not only making them keys but also inserting them into the FacultyInfo objects
        # Define exclude keys map to parse into a list of keys to exclude from final dict
        self.logger.info("Defining exclude keys map...")
        exclude_keys_map = {
            "article_count": True,
            "average_citations": True,
            "doi_citation_map": True,
        }
        self.logger.info(f"Exclude keys map: {exclude_keys_map}")

        self.logger.info("Flattening faculty stats...")
        # List[FacultyInfo.to_dict()]
        flattened_data: List[Dict] = []

        # First level: Categories
        self.logger.info("Iterating through faculty stats...")
        for category_stats in faculty_stats.values():
            self.logger.info(f"Processing category stats: {category_stats}")

            # Second level: faculty_stats dict
            self.logger.info("Converting to dict...")
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
            self.logger.info("Faculty dict converted to dict.")

            self.logger.info("Checking if faculty_stats is in faculty_dict...")
            if "faculty_stats" in faculty_dict:  # Second level: faculty_stats dict
                self.logger.info("Faculty stats found in faculty dict.")

                self.logger.info("Iterating through faculty stats...")
                for faculty_info_obj in faculty_dict["faculty_stats"].values():
                    self.logger.info(f"Processing faculty info obj: {faculty_info_obj}")
                    # Convert FacultyInfo obj to dict and append to flattened_data
                    flattened_data.append(faculty_info_obj)

        self.logger.info("Flattened data appended.")

        self.logger.info("Assigning flattened data to final_faculty_data...")
        self.final_faculty_data = flattened_data
        self.logger.info("Final faculty data assigned.")

        self.logger.info("Writing to file...")
        self._write_to_json(flattened_data, output_path)

    def _serialize_and_save_global_faculty_stats(
        self, *, output_path: str, global_faculty_stats: Dict[str, FacultyStats]
    ) -> None:
        """Serialize and save global faculty statistics to JSON file.

        Args:
            output_path (str): Path where the JSON file will be saved.
            global_faculty_stats (Dict[str, FacultyStats]): Global faculty statistics to serialize.

        Raises:
            IOError: If file writing fails.
        """
        self.logger.info("Serializing and saving global faculty stats...")

        # Step 0: Define exclude keys map to parse into a list of keys to exclude from final dict
        self.logger.info("Defining exclude keys map...")
        exclude_keys_map = {
            "article_count": True,
            "average_citations": True,
            "citation_map": True,
        }
        self.logger.info(f"Exclude keys map: {exclude_keys_map}")

        # Step 1: Flatten and convert to list of dicts
        self.logger.info("Flattening and converting to list of dicts...")
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
        self.logger.info("Flattened and converted to list of dicts.")

        self.logger.info("Assigning flattened data to final_global_faculty_data...")
        self.final_global_faculty_data = data
        self.logger.info("Final global faculty data assigned.")

        self.logger.info("Writing to file...")
        # Step 2: Write to file
        self._write_to_json(data, output_path)

    def _serialize_and_save_category_article_stats(
        self, *, output_path: str, article_stats: Dict[str, CrossrefArticleStats]
    ) -> None:
        """Serialize and save article statistics to JSON file.

        Args:
            output_path (str): Path where the JSON file will be saved.
            article_stats (Dict[str, CrossrefArticleStats]): Article statistics to serialize.

        Raises:
            IOError: If file writing fails.
        """
        self.logger.info("Serializing and saving article stats...")

        self.logger.info("Flattening article stats...")
        flattened_data: List[Dict] = []

        self.logger.info("Iterating through article stats...")
        for category, stats in article_stats.items():
            self.logger.info(f"Processing article stats: {stats}")
            stats_dict = stats.to_dict()

            self.logger.info("Checking if article_citation_map is in stats_dict...")
            if "article_citation_map" in stats_dict:
                self.logger.info("Article citation map found in stats dict.")

                self.logger.info("Iterating through article citation map...")
                for article in stats_dict["article_citation_map"].values():
                    self.logger.info(f"Processing article: {article}")
                    flattened_data.append({**article})
        self.logger.info("Flattened data appended.")

        self.logger.info("Assigning flattened data to final_article_stats_data...")
        self.final_article_stats_data = flattened_data
        self.logger.info("Final article stats data assigned.")

        self.logger.info("Writing to file...")
        self._write_to_json(flattened_data, output_path)

    def _serialize_and_save_articles(
        self, *, output_path: str, articles: List[CrossrefArticleDetails]
    ) -> None:
        """Serialize and save article details to JSON file.

        Args:
            output_path (str): Path where the JSON file will be saved.
            articles (List[CrossrefArticleDetails]): Article details to serialize.

        Raises:
            IOError: If file writing fails.
        """
        self.logger.info("Serializing and saving articles...")

        self.logger.info("Converting to list of dicts...")
        # Convert each CrossrefArticleDetails object to a dict
        article_dicts: List[Dict] = [article.to_dict() for article in articles]
        self.logger.info("Converted to list of dicts.")

        self.logger.info("Assigning to final_article_data...")
        self.final_article_data = article_dicts
        self.logger.info("Final article data assigned.")

        self.logger.info("Writing to file...")
        # Write to file
        self._write_to_json(article_dicts, output_path)

    def _flatten_to_list(self, data: Union[Dict, List]) -> List[Dict]:
        """Recursively flatten nested dictionaries/lists into a flat list.

        Args:
            data (Union[Dict, List]): Nested structure of dictionaries and lists.

        Returns:
            List[Dict]: Flattened list of dictionaries.

        Example:
            Input: {"cat1": {"article_map": {"doi1": {...}, "doi2": {...}}}}
            Output: [{...}, {...}]  # List of article dictionaries
        """
        self.logger.info("Flattening...")
        flattened: List[Dict] = []

        self.logger.info("Checking if data is a dict...")
        if isinstance(data, dict):
            self.logger.info("Data is a dict. Iterating through values...")
            for value in data.values():
                flattened.extend(self._flatten_to_list(value))
        elif isinstance(data, list):
            self.logger.info("Data is a list. Iterating through items...")
            for item in data:
                flattened.extend(self._flatten_to_list(item))
        else:  # Base case: found a non-dict, non-list value
            self.logger.info("Data is a non-dict, non-list value. Appending...")
            if isinstance(data, dict):  # If it's a dictionary, add it
                flattened.append(data)

        self.logger.info("Flattened.")
        return flattened

    def _write_to_json(self, data: Union[List[Dict], Dict], output_path: str) -> None:
        """Write data to JSON file, handling extend mode.

        Args:
            data (Union[List[Dict], Dict]): Data to write to file.
            output_path (str): Path where the JSON file will be saved.

        Raises:
            IOError: If file operations fail.
        """
        self.logger.info("Checking if extending...")
        if self.extend:
            self.logger.info("Extending...")
            with open(output_path, "r") as json_file:
                existing_data: Union[List[Dict], Dict] = json.load(json_file)
            self.logger.info("Existing data loaded.")

            self.logger.info("Checking if data is a list...")
            if isinstance(data, list):
                self.logger.info("Data is a list. Extending...")
                existing_data.extend(data)
            else:
                self.logger.info("Data is not a list. Updating...")
                existing_data.update(data)
            self.logger.info("Data updated.")
            data: Union[List[Dict], Dict] = existing_data

        self.logger.info("Dumping data to file...")
        with open(output_path, "w") as json_file:
            json.dump(data, json_file, indent=4)


if __name__ == "__main__":
    import tempfile

    # Create a test CategoryInfo object
    test_category = CategoryInfo(
        _id="Psychology",
        url="Psychology",
        category_name="Psychology",
        faculty_count=6,
        department_count=4,
        article_count=3,
        faculty={"Sook-Hyun Kim", "Jose I. Juncosa", "Suzanne L. Osman"},
        departments={
            "Department of Psychology, Salisbury University, Salisbury, MD, USA"
        },
        titles={"Korean fathers' immigration experience"},
        tc_count=0,
        citation_average=0.0,
        doi_list={"10.1177/10778012241234897"},
        themes={"Parenting Challenges", "Cultural Identity"},
    )

    # Create the input dictionary format
    category_data = {"Psychology": test_category}

    # Create a minimal orchestrator instance
    with tempfile.TemporaryDirectory() as temp_dir:
        orchestrator = CategoryDataOrchestrator(
            data=[],
            output_dir_path=temp_dir,
            category_processor=None,
            faculty_postprocessor=None,
            strategy_factory=None,
            dataclass_factory=None,
            warning_manager=None,
            utilities=None,
        )

        # Test the serialization
        output_path = os.path.join(temp_dir, "test_categories.json")
        print("\nTesting category serialization:")
        print(f"Input category data: {category_data}")

        orchestrator._serialize_and_save_category_data(
            output_path=output_path, category_data=category_data
        )

        print("\nAfter serialization:")
        print(
            f"Has final_category_data: {hasattr(orchestrator, 'final_category_data')}"
        )
        if hasattr(orchestrator, "final_category_data"):
            print(
                f"Length of final_category_data: {len(orchestrator.final_category_data)}"
            )
            print(f"Content: {orchestrator.final_category_data}")

        # Test retrieval
        try:
            retrieved_data = orchestrator.get_final_category_data()
            print("\nSuccessfully retrieved data:")
            print(f"Length: {len(retrieved_data)}")
            print(f"Content: {retrieved_data}")

            # Also check the JSON file
            print("\nJSON file content:")
            with open(output_path, "r") as f:
                json_content = json.load(f)
                print(f"JSON length: {len(json_content)}")
                print(f"JSON content: {json_content}")

        except ValueError as e:
            print(f"\nError retrieving data: {e}")
