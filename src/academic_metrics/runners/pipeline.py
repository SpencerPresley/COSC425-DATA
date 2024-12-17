import json
import logging
import os
from collections import defaultdict
from typing import Any, Callable, Dict, List, TypedDict
from urllib.parse import quote, unquote

from academic_metrics.constants import (
    INPUT_FILES_DIR_PATH,
    LOG_DIR_PATH,
    OUTPUT_FILES_DIR_PATH,
    SPLIT_FILES_DIR_PATH,
)
from academic_metrics.core import CategoryProcessor
from academic_metrics.postprocessing import (
    FacultyPostprocessor,
    DepartmentPostprocessor,
)
from academic_metrics.data_collection import CrossrefWrapper, Scraper
from academic_metrics.DB import DatabaseWrapper
from academic_metrics.enums import AttributeTypes
from academic_metrics.factories import (
    DataClassFactory,
    ClassifierFactory,
    StrategyFactory,
)
from academic_metrics.orchestrators import (
    CategoryDataOrchestrator,
    ClassificationOrchestrator,
)
from academic_metrics.utils import (
    APIKeyValidator,
    Taxonomy,
    Utilities,
    WarningManager,
    MinHashUtility,
)
from academic_metrics.configs import configure_logging, DEBUG


class SaveOfflineKwargs(TypedDict):
    offline: bool
    run_crossref_before_file_load: bool
    make_files: bool
    extend: bool


class PipelineRunner:
    """Orchestrates the academic metrics data processing pipeline.

    This class manages the end-to-end process of collecting, processing, and storing
    academic publication data. It handles data collection from Crossref, classification
    of publications, generation of statistics, and storage in MongoDB.

    Attributes:
        SAVE_OFFLINE_KWARGS (SaveOfflineKwargs): Default configuration for offline processing.
        logger (logging.Logger): Pipeline-wide logger instance.
        ai_api_key (str): API key for AI services.
        db_name (str): Name of the MongoDB database.
        mongodb_url (str): URL for MongoDB connection.
        db (DatabaseWrapper): Database interface instance.
        scraper (Scraper): Web scraping utility instance.
        crossref_wrapper (CrossrefWrapper): Crossref API interface instance.
        taxonomy (Taxonomy): Publication taxonomy utility.
        warning_manager (WarningManager): Warning logging utility.
        strategy_factory (StrategyFactory): Strategy pattern factory.
        utilities (Utilities): General utility functions.
        classification_orchestrator (ClassificationOrchestrator): Publication classifier.
        dataclass_factory (DataClassFactory): Data class creation utility.
        category_processor (CategoryProcessor): Category statistics processor.
        faculty_postprocessor (FacultyPostprocessor): Faculty data processor.
        department_postprocessor (DepartmentPostprocessor): Department data processor.
        debug (bool): Debug mode flag.

    Methods:
        run_pipeline: Executes the main data processing pipeline.
        _create_taxonomy: Creates a new Taxonomy instance.
        _create_classifier_factory: Creates a new ClassifierFactory instance.
        _create_warning_manager: Creates a new WarningManager instance.
        _create_strategy_factory: Creates a new StrategyFactory instance.
        _create_utilities_instance: Creates a new Utilities instance.
        _create_classification_orchestrator: Creates a new ClassificationOrchestrator.
        _create_orchestrator: Creates a new CategoryDataOrchestrator.
        _get_acf_func: Returns the abstract classifier factory function.
        _validate_api_key: Validates the provided API key.
        _make_files: Creates split files from input files.
        _load_files: Loads and returns data from split files.
        _create_dataclass_factory: Creates a new DataClassFactory instance.
        _create_crossref_wrapper: Creates a new CrossrefWrapper instance.
        _create_category_processor: Creates a new CategoryProcessor instance.
        _create_faculty_postprocessor: Creates a new FacultyPostprocessor instance.
        _create_scraper: Creates a new Scraper instance.
        _create_db: Creates a new DatabaseWrapper instance.
        _encode_affiliation: URL encodes an affiliation string.
    """

    SAVE_OFFLINE_KWARGS: SaveOfflineKwargs = {
        "offline": False,
        "run_crossref_before_file_load": False,
        "make_files": False,
        "extend": False,
    }

    def __init__(
        self,
        ai_api_key: str,
        crossref_affiliation: str,
        data_from_month: int,
        data_to_month: int,
        data_from_year: int,
        data_to_year: int,
        mongodb_url: str,
        db_name: str | None = "Site_Data",
        debug: bool | None = False,
        pre_classification_model: str | None = "gpt-4o-mini",
        classification_model: str | None = "gpt-4o-mini",
        theme_model: str | None = "gpt-4o-mini",
    ):
        """Initialize the PipelineRunner with necessary configurations and dependencies.

        Args:
            ai_api_key (str): API key for AI services (e.g., OpenAI).
            crossref_affiliation (str): Institution name to search for in Crossref.
            data_from_year (int): Start year for publication data collection.
            data_to_year (int): End year for publication data collection.
            mongodb_url (str): Connection URL for MongoDB instance.
            db_name (str, optional): Name of the MongoDB database. Defaults to "Site_Data".
            debug (bool, optional): Enable debug mode for additional logging and controls. Defaults to False.

        Raises:
            Exception: If logger setup fails or required dependencies cannot be initialized.
        """
        self.logger: logging.Logger = configure_logging(__name__, "pipeline", DEBUG)
        self.logger.info("Initializing PipelineRunner...")
        self.logger.info("PipelineRunner logger initialized successfully")

        self.logger.info("Initializing PipelineRunner dependencies...")
        self.ai_api_key: str = ai_api_key
        self.db_name: str = db_name
        self.mongodb_url: str = mongodb_url

        self.logger.info("Creating DatabaseWrapper instance...")
        self.db: DatabaseWrapper = self._create_db()
        self.logger.info("DatabaseWrapper instance created successfully")

        self.logger.info("Creating Scraper instance...")
        self.scraper: Scraper = self._create_scraper()
        self.logger.info("Scraper instance created successfully")

        self.logger.info("Creating CrossrefWrapper instance...")
        self.crossref_wrapper: CrossrefWrapper = self._create_crossref_wrapper(
            affiliation=self._encode_affiliation(crossref_affiliation),
            from_month=data_from_month,
            to_month=data_to_month,
            from_year=data_from_year,
            to_year=data_to_year,
        )
        self.logger.info("CrossrefWrapper instance created successfully")

        self.logger.info("Creating Taxonomy instance...")
        self.taxonomy: Taxonomy = self._create_taxonomy()
        self.logger.info("Taxonomy instance created successfully")

        self.logger.info("Creating WarningManager instance...")
        self.warning_manager: WarningManager = self._create_warning_manager()
        self.logger.info("WarningManager instance created successfully")

        self.logger.info("Creating StrategyFactory instance...")
        self.strategy_factory: StrategyFactory = self._create_strategy_factory()
        self.logger.info("StrategyFactory instance created successfully")

        self.logger.info("Creating Utilities instance...")
        self.utilities: Utilities = self._create_utilities_instance()
        self.logger.info("Utilities instance created successfully")

        self.logger.info("Creating ClassificationOrchestrator instance...")
        self.classification_orchestrator: ClassificationOrchestrator = (
            self._create_classification_orchestrator()
        )
        self.logger.info("ClassificationOrchestrator instance created successfully")

        self.logger.info("Creating DataClassFactory instance...")
        self.dataclass_factory: DataClassFactory = self._create_dataclass_factory()
        self.logger.info("DataClassFactory instance created successfully")

        self.logger.info("Creating CategoryProcessor instance...")
        self.category_processor: CategoryProcessor = self._create_category_processor()
        self.logger.info("CategoryProcessor instance created successfully")

        self.logger.info("Creating MinHashUtility instance...")
        self.minhash_util: MinHashUtility = self._create_minhash_util()
        self.logger.info("MinHashUtility instance created successfully")

        self.logger.info("Creating FacultyPostprocessor instance...")
        self.faculty_postprocessor: FacultyPostprocessor = (
            self._create_faculty_postprocessor(minhash_util=self.minhash_util)
        )
        self.logger.info("FacultyPostprocessor instance created successfully")

        self.logger.info("Creating DepartmentPostprocessor instance...")
        self.department_postprocessor: DepartmentPostprocessor = (
            self._create_department_postprocessor(minhash_util=self.minhash_util)
        )
        self.logger.info("DepartmentPostprocessor instance created successfully")

        self.logger.info("Setting debug mode...")
        self.debug: bool = debug
        self.logger.info("Debug mode set successfully")

        self.logger.info("Setting pre-classification-model...")
        self.pre_classification_model: str | None = pre_classification_model
        self.logger.info("Pre-classification-model set successfully")

        self.logger.info("Setting classification-model...")
        self.classification_model: str | None = classification_model
        self.logger.info("Classification-model set successfully")

        self.logger.info("Setting theme-model...")
        self.theme_model: str | None = theme_model
        self.logger.info("Theme-model set successfully")

        self.logger.info("PipelineRunner initialized successfully")

    def run_pipeline(
        self,
        save_offline_kwargs: SaveOfflineKwargs = SAVE_OFFLINE_KWARGS,
        test_filtering: bool | None = False,
        save_to_db: bool | None = True,
    ):
        """Execute the main data processing pipeline.

        This method orchestrates the entire pipeline process:
        1. Retrieves existing DOIs from database
        2. Collects new publication data from Crossref
        3. Filters out duplicate articles
        4. Runs AI classification on publications
        5. Processes and generates category statistics
        6. Saves processed data to MongoDB

        Args:
            save_offline_kwargs (SaveOfflineKwargs, optional): Configuration for offline processing.
                Defaults to SAVE_OFFLINE_KWARGS.
                - offline: Whether to run in offline mode
                - run_crossref_before_file_load: Run Crossref before loading files
                - make_files: Generate new split files
                - extend: Extend existing data

        Raises:
            Exception: If there are errors in data processing or database operations.
        """
        self.logger.info("Running pipeline...")

        # Get the existing DOIs from the database
        # so that we don't process duplicates
        self.logger.info("Getting existing DOIs from database...")
        existing_dois: List[str] = []
        if save_to_db:
            existing_dois: List[str] = self.db.get_dois()
        self.logger.info(f"Found {len(existing_dois)} existing DOIs in database")

        # Get data from crossref for the school and date range
        self.logger.info("Getting data from Crossref...")
        data: List[Dict[str, Any]] = []
        if save_offline_kwargs["offline"]:
            if save_offline_kwargs["run_crossref_before_file_load"]:
                data: List[Dict[str, Any]] = self.crossref_wrapper.run_all_process()
            if save_offline_kwargs["make_files"]:
                self._make_files()
            data: List[Dict[str, Any]] = self._load_files()
        else:
            # Fetch raw data from Crossref api for the year range
            # and get out the result list containing the raw data.
            data: List[Dict[str, Any]] = (
                self.crossref_wrapper.run_afetch_yrange().get_result_list()
            )
        self.logger.info(
            "Filtering out articles whose DOIs are already in the db or those that are not found..."
        )
        # Then filter out articles whose DOIs are already
        # in the db or those that are not found.
        already_existing_count: int = 0
        filtered_data: List[Dict[str, Any]] = []
        for article in data:
            # Get the DOI out of the article item
            attribute_results: List[str] = self.utilities.get_attributes(
                article, [AttributeTypes.CROSSREF_DOI]
            )
            # Unpack the DOI from the dict returned by get_attributes
            doi = (
                attribute_results[AttributeTypes.CROSSREF_DOI][1]
                if attribute_results[AttributeTypes.CROSSREF_DOI][0]
                else None
            )
            # Only keep articles that have a DOI and aren't already in the database
            if doi is not None:
                if doi not in existing_dois:
                    filtered_data.append(article)
                else:
                    already_existing_count += 1
            else:
                self.logger.warning(f"Article with no DOI: {article}")
                continue

        self.logger.info(f"Filtered out {already_existing_count}/{len(data)} articles")
        self.logger.info(f"Articles to process: {len(filtered_data)}")
        self.logger.info("Initial filtering complete")

        if len(filtered_data) == 0:
            self.logger.info("No articles to process")
            return

        # Then set data to filtered data so we don't
        # keep the raw data floating in memory.
        data: List[Dict[str, Any]] = filtered_data

        # Now run final processing to have `Scraper` fetch missing abstracts.
        # Reset the result list in `CrossrefWrapper` so it doesn't
        # run on the original raw data, and instead runs on the filtered data.
        self.logger.info("Resetting CrossrefWrapper result list...")
        self.crossref_wrapper.result = data
        self.logger.info("CrossrefWrapper result list reset successfully")

        # Run the final processing to fetch missing abstracts
        # and get out the final data.
        # Again, we don't want to keep the raw data floating in memory,
        # so we reassign `data` to the the result list returned by `.get_result_list()`.
        self.logger.info("Running final processing to fetch missing abstracts...")
        data = self.crossref_wrapper.final_data_process().get_result_list()
        self.logger.info("Final processing complete")

        if len(data) == 0:
            self.logger.info(
                "None of the remaining articles have abstracts or none could be retrieved"
            )
            return

        if test_filtering:
            print(f"\n\nFiltered out {already_existing_count} articles\n\n")
            print(
                f"\n\nFILTERED DATA VAR CONTENTS:\n{json.dumps(filtered_data, indent=4)}\n\n"
            )
            print(f"\n\nDATA VAR CONTENTS:\n{data}\n\n")
            return

        self.logger.info(f"\n\nDATA: {data}\n\n")

        if self.debug:
            print(f"There are {len(data)} articles to process.")
            response: str = input("Would you like to slice the data? (y/n)")
            if response == "y":
                res: str = input("How many articles would you like to process?")
                data = data[: int(res)]
                self.logger.info(f"\n\nSLICED DATA:\n{data}\n\n")

        # Run classification on all data
        # comment out to run without AI for testing
        self.logger.info("Running classification...")
        data = self.classification_orchestrator.run_classification(
            data,
            pre_classification_model=self.pre_classification_model,
            classification_model=self.classification_model,
            theme_model=self.theme_model,
        )
        self.logger.info("Classification complete")

        with open("classified_data.json", "w") as file:
            json.dump(data, file, indent=4)

        # Process classified data and generate category statistics
        self.logger.info(
            "Processing classified data and generating category statistics..."
        )
        category_orchestrator: CategoryDataOrchestrator = self._create_orchestrator(
            data=data,
            extend=save_offline_kwargs["extend"],
        )
        category_orchestrator.run_orchestrator()
        self.logger.info("Category statistics processing complete")

        # Get all the processed data from CategoryDataOrchestrator
        self.logger.info("Getting final data...")

        self.logger.info("Getting final category data...")
        category_data: List[Dict[str, Any]] = (
            category_orchestrator.get_final_category_data()
        )
        self.logger.info("Final category data retrieved successfully")

        self.logger.info("Getting final faculty data...")
        # faculty_data = self.category_orchestrator.get_final_faculty_data()
        article_data: List[Dict[str, Any]] = (
            category_orchestrator.get_final_article_data()
        )
        self.logger.info("Final article data retrieved successfully")

        self.logger.info("Getting final global faculty data...")
        global_faculty_data: List[Dict[str, Any]] = (
            category_orchestrator.get_final_global_faculty_data()
        )
        self.logger.info("Final global faculty data retrieved successfully")

        if save_to_db:
            self.logger.info("Attempting to save data to database...")
            try:
                self.db.insert_categories(category_data)
                self.logger.info(
                    f"""Successfully inserted {len(category_data)} categories into database"""
                )
            except Exception as e:
                self.logger.error(f"Error saving to database: {e}")

            try:
                self.db.insert_articles(article_data)
                self.logger.info(
                    f"""Successfully inserted {len(article_data)} articles into database"""
                )
            except Exception as e:
                self.logger.error(f"Error saving to database: {e}")

            try:
                self.db.insert_faculty(global_faculty_data)
                self.logger.info(
                    f"""Successfully inserted {len(global_faculty_data)} faculty into database"""
                )
            except Exception as e:
                self.logger.error(f"Error saving to database: {e}")

    def test_run(self):
        with open("test_processed_category_data.json", "r") as file:
            category_data: List[Dict[str, Any]] = json.load(file)

        try:
            self.db.insert_categories(category_data)
            self.logger.info(
                f"""Successfully inserted {len(category_data)} categories into database"""
            )
        except Exception as e:
            self.logger.error(f"Error saving to database: {e}")

        with open("test_processed_article_stats_obj_data.json", "r") as file:
            article_data: List[Dict[str, Any]] = json.load(file)

        try:
            self.db.insert_articles(article_data)
            self.logger.info(
                f"""Successfully inserted {len(article_data)} articles into database"""
            )
        except Exception as e:
            self.logger.error(f"Error saving to database: {e}")

        with open("test_processed_global_faculty_stats_data.json", "r") as file:
            global_faculty_data: List[Dict[str, Any]] = json.load(file)

        try:
            self.db.insert_faculty(global_faculty_data)
            self.logger.info(
                f"""Successfully inserted {len(global_faculty_data)} faculty into database"""
            )
        except Exception as e:
            self.logger.error(f"Error saving to database: {e}")

    def _create_taxonomy(self) -> Taxonomy:
        """Create a new Taxonomy instance for publication classification.

        Returns:
            Taxonomy: A new instance of the Taxonomy utility class.
        """
        return Taxonomy()

    def _create_classifier_factory(self) -> ClassifierFactory:
        """Create a new ClassifierFactory for generating publication classifiers.

        Returns:
            ClassifierFactory: A factory instance configured with taxonomy and AI API key.
        """
        return ClassifierFactory(
            taxonomy=self.taxonomy,
            ai_api_key=self.ai_api_key,
        )

    def _create_warning_manager(self) -> WarningManager:
        """Create a new WarningManager for handling pipeline warnings.

        Returns:
            WarningManager: A new instance of the warning management utility.
        """
        return WarningManager()

    def _create_strategy_factory(self) -> StrategyFactory:
        """Create a new StrategyFactory for generating processing strategies.

        Returns:
            StrategyFactory: A new instance of the strategy factory.
        """
        return StrategyFactory()

    def _create_utilities_instance(self) -> Utilities:
        """Create a new Utilities instance with required dependencies.

        Returns:
            Utilities: A utility instance configured with strategy factory and warning manager.
        """
        return Utilities(
            strategy_factory=self.strategy_factory,
            warning_manager=self.warning_manager,
        )

    def _create_classification_orchestrator(self) -> ClassificationOrchestrator:
        """Create a new ClassificationOrchestrator for managing publication classification.

        Returns:
            ClassificationOrchestrator: An orchestrator instance configured with classifier factory and utilities.
        """
        return ClassificationOrchestrator(
            abstract_classifier_factory=self._get_acf_func(),
            utilities=self.utilities,
        )

    def _create_orchestrator(
        self, data: List[Dict[str, Any]], extend: bool
    ) -> CategoryDataOrchestrator:
        """Create a new CategoryDataOrchestrator for managing category data processing.

        Args:
            data (List[Dict[str, Any]]): List of publication data to process.
            extend (bool): Whether to extend existing data.

        Returns:
            CategoryDataOrchestrator: An orchestrator instance configured with all necessary processors and utilities.
        """
        return CategoryDataOrchestrator(
            data=data,
            output_dir_path=OUTPUT_FILES_DIR_PATH,
            category_processor=self.category_processor,
            faculty_postprocessor=self.faculty_postprocessor,
            department_postprocessor=self.department_postprocessor,
            warning_manager=self.warning_manager,
            strategy_factory=self.strategy_factory,
            utilities=self.utilities,
            dataclass_factory=self.dataclass_factory,
            extend=extend,
        )

    def _get_acf_func(self) -> Callable[[Dict[str, str]], ClassifierFactory]:
        """Get the abstract classifier factory function.

        Returns:
            Callable[[Dict[str, str]], ClassifierFactory]: A function that creates an AbstractClassifier
                given a dictionary of DOIs and abstracts.
        """
        return self._create_classifier_factory().abstract_classifier_factory

    def _validate_api_key(self, validator: APIKeyValidator, api_key: str) -> None:
        """Validate the provided API key.

        Args:
            validator (APIKeyValidator): Validator instance to check the API key.
            api_key (str): API key to validate.

        Raises:
            ValueError: If the API key is invalid.
        """
        if not validator.is_valid(api_key=api_key):
            raise ValueError(
                "Invalid API key. Please check your API key and try again."
            )

    def _make_files(self) -> None:
        """Create split files from input files for offline processing.

        Raises:
            Exception: If input directory contains no files to process.
        """
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

    def _load_files(self) -> List[Dict[str, Any]]:
        """Load all split files into a list of dictionaries.

        Returns:
            List[Dict[str, Any]]: List of loaded data from split files.

        Notes:
            Warnings are logged for any files that fail to load.
        """
        data_list: List[Dict[str, Any]] = []
        for file_name in os.listdir(SPLIT_FILES_DIR_PATH):
            file_path: str = os.path.join(SPLIT_FILES_DIR_PATH, file_name)
            if not os.path.isfile(file_path):
                continue

            try:
                with open(file_path, "r") as file:
                    data: Dict[str, Any] = json.load(file)
                    data_list.append(data)
            except Exception as e:
                self.warning_manager.log_warning(
                    "File Loading", f"Error loading file: {file_path}. Error: {e}"
                )
                raise e

        return data_list

    def _create_dataclass_factory(self) -> DataClassFactory:
        """Create a new DataClassFactory for generating data classes.

        Returns:
            DataClassFactory: A new instance of the data class factory.
        """
        return DataClassFactory()

    def _create_crossref_wrapper(self, **kwargs) -> CrossrefWrapper:
        """Create a new CrossrefWrapper for interacting with the Crossref API.

        Args:
            **kwargs: Keyword arguments for CrossrefWrapper configuration.

        Returns:
            CrossrefWrapper: A configured CrossrefWrapper instance.
        """
        if "scraper" not in kwargs:
            kwargs["scraper"] = self.scraper if self.scraper else self._create_scraper()
        return CrossrefWrapper(**kwargs)

    def _create_category_processor(self) -> CategoryProcessor:
        """Create a new CategoryProcessor for processing publication categories.

        Returns:
            CategoryProcessor: A processor instance configured with utilities and factories.
        """
        return CategoryProcessor(
            utils=self.utilities,
            dataclass_factory=self.dataclass_factory,
            warning_manager=self.warning_manager,
            taxonomy_util=self.taxonomy,
        )

    def _create_minhash_util(self) -> MinHashUtility:
        """Create a new MinHashUtility instance for minhash operations.

        Returns:
            MinHashUtility: A new instance of the minhash utility.
        """
        return MinHashUtility(
            num_hashes=100,
        )

    def _create_faculty_postprocessor(
        self, minhash_util: MinHashUtility
    ) -> FacultyPostprocessor:
        """Create a new FacultyPostprocessor for processing faculty data.

        Returns:
            FacultyPostprocessor: A new instance of the faculty post-processor.
        """
        return FacultyPostprocessor(minhash_util=minhash_util)

    def _create_department_postprocessor(
        self, minhash_util: MinHashUtility
    ) -> DepartmentPostprocessor:
        """Create a new DepartmentPostprocessor for processing department data.

        Returns:
            DepartmentPostprocessor: A new instance of the department post-processor.
        """
        return DepartmentPostprocessor(minhash_util=minhash_util, threshold=0.5)

    def _create_scraper(self) -> Scraper:
        """Create a new Scraper instance for web scraping.

        Returns:
            Scraper: A scraper instance configured with the AI API key.
        """
        return Scraper(api_key=self.ai_api_key)

    def _create_db(self) -> DatabaseWrapper:
        """Create a new DatabaseWrapper for database operations.

        Returns:
            DatabaseWrapper: A database wrapper configured with connection details.
        """
        return DatabaseWrapper(db_name=self.db_name, mongo_url=self.mongodb_url)

    @staticmethod
    def _encode_affiliation(affiliation: str) -> str:
        """URL encode an affiliation string if it's not already encoded.

        Checks if the string is already properly URL-encoded by:
        1. Decoding it with unquote()
        2. Re-encoding it with quote()
        3. Comparing to original - if they match, it was already encoded

        Args:
            affiliation (str): Institution name to encode (e.g. "Salisbury University"
                or "Salisbury%20University")

        Returns:
            str: URL-encoded string (e.g. "Salisbury%20University")
        """
        return (
            affiliation
            if quote(unquote(affiliation)) == affiliation
            else quote(affiliation)
        )


if __name__ == "__main__":
    import argparse
    from dotenv import load_dotenv

    load_dotenv()
    ai_api_key = os.getenv("OPENAI_API_KEY")

    # Create argument parser
    parser = argparse.ArgumentParser(description="Run the academic metrics pipeline")
    parser.add_argument(
        "--test-run", action="store_true", help="Run in test mode using local MongoDB"
    )
    parser.add_argument(
        "--pre-classification-model",
        type=str,
        default="gpt-4o-mini",
        choices=["gpt-4o-mini", "gpt-4o"],
        help="Valid pre-classification-model's are 'gpt-4o-mini' or 'gpt-4o'",
    )
    parser.add_argument(
        "--classification-model",
        type=str,
        default="gpt-4o-mini",
        choices=["gpt-4o-mini", "gpt-4o"],
        help="Valid classification-model's are 'gpt-4o-mini' or 'gpt-4o'",
    )
    parser.add_argument(
        "--theme-model",
        type=str,
        default="gpt-4o-mini",
        choices=["gpt-4o-mini", "gpt-4o"],
        help="Valid theme-model's are 'gpt-4o-mini' or 'gpt-4o'",
    )

    args = parser.parse_args()

    # Configure logging
    logger = configure_logging(__name__, "main", log_level=logging.DEBUG)

    pre_classification_model = args.pre_classification_model
    classification_model = args.classification_model
    theme_model = args.theme_model

    if args.test_run:
        # Load local mongodb url
        logger.info("Running in test mode using local MongoDB...")
        mongodb_url = os.getenv("LOCAL_MONGODB_URL")
        pipeline = PipelineRunner(
            ai_api_key=ai_api_key,
            crossref_affiliation="Salisbury University",
            data_from_year=2024,
            data_to_year=2024,
            mongodb_url=mongodb_url,
        )

        # Execute test run
        pipeline.test_run()
    else:
        # Normal pipeline execution
        logger.info(f"Running in production mode using Live MongoDB URL")
        mongodb_url = os.getenv("LOCAL_MONGODB_URL")
        years = ["2019"]
        months = ["11"]

        processed_dict = defaultdict(list)

        for year in years:

            current_months = months[8:] if year == "2012" else months

            for month in current_months:
                pipeline_runner = PipelineRunner(
                    ai_api_key=ai_api_key,
                    crossref_affiliation="Salisbury University",
                    data_from_month=int(month),
                    data_to_month=int(month),
                    data_from_year=int(year),
                    data_to_year=int(year),
                    mongodb_url=mongodb_url,
                    pre_classification_model=pre_classification_model,
                    classification_model=classification_model,
                    theme_model=theme_model,
                )
                pipeline_runner.run_pipeline()
                processed_dict[year].append(month)
                logger.info(f"Processed year: {year}, month: {month}")

    logger.info(f"Processed data: {json.dumps(processed_dict, indent=4)}")

    with open("processed_data.json", "w") as file:
        json.dump(processed_dict, file, indent=4)
