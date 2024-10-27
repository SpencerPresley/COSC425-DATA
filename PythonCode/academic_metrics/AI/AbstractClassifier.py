import os
import json
import logging
from typing import List, Dict, Any, Set
from dotenv import load_dotenv
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
from academic_metrics.data_models.ai_pydantic_models import ClassificationOutput, ThemeAnalysis

class AbstractClassifier:
    """
    AbstractClassifier is a class designed to classify research paper abstracts into a hierarchical taxonomy and process their themes.
        __init__(self, taxonomy, abstracts: List[str]):
            Initializes the AbstractClassifier with the given taxonomy and abstracts.
        _load_env(self):
            Loads the environment variables.
        _initialize_chain_manager(self):
            Initializes and returns a ChainManager instance.
        create_classification_chain(self):
            Creates the classification chain for the classifier.
        create_theme_chain(self):
            Creates the theme recognition chain for the classifier.
        classify_abstract(self, abstract: str, abstract_index: int, categories: List[str], level: str, method_json_output, abstract_chain_output, abstract_summary_output, parent_category=None):
            Classifies a single abstract into the taxonomy at the specified level.
        process_all_themes(self):
            Processes the themes of all abstracts.
        extract_classified_categories(self, classification_output: ClassificationOutput) -> List[str]:
            Extracts the classified categories from the classification output.
        get_json_classification_form(self) -> str:
            Returns the JSON classification form.
        classify(self):
            Classifies all abstracts and processes their themes.
        _get_json_outputs(self, index):
            Retrieves the JSON outputs for a given abstract index.
        save_classification_results(self, output_path: str):
            Saves the classification results to a file.
        get_raw_classification_outputs(self):
            Returns the raw classification outputs.
        get_raw_theme_results(self):
            Returns the raw theme results.
        save_raw_classification_results(self, output_path: str):
            Saves the raw classification results to a file.
        save_raw_theme_results(self, output_path: str):
            Saves the raw theme results to a file.
    """
    def __init__(self, taxonomy: Taxonomy, abstracts: List[str], is_test_run: bool = False):
        # Logger setup
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(logging.StreamHandler())
        self.logger.info("Initializing AbstractClassifier")
        
        # Taxonomy and abstracts
        self.taxonomy: Taxonomy = taxonomy
        self.abstracts: List[str] = abstracts
        self.is_test_run: bool = is_test_run
        self.pre_classification_results: Dict[str, Dict[str, Any]] = None
        
        # Pre-classification results
        if not self.is_test_run:
            self.pre_classification_results = {i: {} for i in range(len(abstracts))}
            self.logger.info("Initialized pre-classification results")
        self.logger.info("Initialized taxonomy and abstracts")
        
        # Paths to directories
        self.current_directory: str = os.path.dirname(os.path.abspath(__file__))
        self.path_to_core_data_directory: str = os.path.join(self.current_directory, "..", "..", "data", "core")
        self.path_to_outputs_directory: str = os.path.join(self.path_to_core_data_directory, "ai_outputs")
        self.path_to_methods_directory: str = os.path.join(self.path_to_outputs_directory, "methods")
        self.path_to_sentence_analysis_directory: str = os.path.join(self.path_to_outputs_directory, "sentence_analysis")
        self.path_to_summary_directory: str = os.path.join(self.path_to_outputs_directory, "summaries")
        self.path_to_raw_themes_directory: str = os.path.join(self.path_to_outputs_directory, "raw_themes")
        self.path_to_classification_results_directory: str = os.path.join(self.path_to_outputs_directory, "classifications")
        self.path_to_raw_classification_outputs_directory: str = os.path.join(self.path_to_outputs_directory, "classifications_raw")
        
        # Classification results and category themes
        self.classification_results: Dict[str, Dict[str, Any]] = {f"abstract_{i}": {} for i in range(len(abstracts))}
        self.category_themes: Dict[str, Set[str]] = {}
        
        # Raw outputs
        self.raw_classification_outputs: List[Dict[str, Any]] = []
        self.raw_theme_outputs: Dict[str, Dict[str, Any]] = {f"abstract_{i}": {} for i in range(len(abstracts))}
        
        # Environment and chain managers
        self._load_env()
        self.classification_chain_manager = self._initialize_chain_manager()
        self.logger.info("Initialized classification chain manager")
        self.theme_chain_manager = self._initialize_chain_manager()
        self.logger.info("Initialized theme chain manager")
        
    # Load environment variables
    def _load_env(self):
        return load_dotenv()

    # Initialize chain manager
    def _initialize_chain_manager(self):
        api_key: str = os.getenv("OPENAI_API_KEY")
        return ChainManager(llm_model="gpt-4o-mini", api_key=api_key, llm_temperature=0.7)

    # Run pre-classification chains
    def run_pre_classification_chains(self):
        pass
    
    # Create classification chain
    def create_classification_chain(self):
        self.classification_chain_manager.add_chain_layer(
            system_prompt=CLASSIFICATION_SYSTEM_MESSAGE,
            human_prompt=HUMAN_MESSAGE_PROMPT,
            parser_type="pydantic",
            return_type="json",
            pydantic_output_model=ClassificationOutput,
            ignore_output_passthrough_key_name_error=True
        )
        
    # Create theme chain
    def create_theme_chain(self):
        self.theme_chain_manager.add_chain_layer(
            system_prompt=THEME_RECOGNITION_SYSTEM_MESSAGE,
            human_prompt=HUMAN_MESSAGE_PROMPT,
            parser_type="pydantic",
            return_type="json",
            pydantic_output_model=ThemeAnalysis,
            ignore_output_passthrough_key_name_error=True
        )
        
    # Get themes for categories
    def get_themes_for_categories(self, categories: List[str]) -> List[str]:
        themes: Set[str] = set()
        for category in categories:
            themes.update(self.category_themes.get(category, []))
        return list(themes)
      
    # Update category themes
    def update_category_themes(self, categories: List[str], new_themes: List[str]):
        for category in categories:
            if category not in self.category_themes:
                self.category_themes[category] = set()
            self.category_themes[category].update(new_themes)
    
    # Get categories for abstract
    def get_categories_for_abstract(self, abstract_index: int) -> List[str]:
        categories: List[str] = []
        abstract_result: Dict[str, Any] = self.classification_results.get(f"abstract_{abstract_index}", {})
        
        # Extract categories
        def extract_categories(result: Dict[str, Any], prefix: str = ''):
            for key, value in result.items():
                full_category: str = f"{prefix}{key}" if prefix else key
                categories.append(full_category)
                if isinstance(value, dict):
                    extract_categories(value, f"{full_category}/")

        extract_categories(abstract_result)
        return categories
    
    # Classify abstract
    def classify_abstract(self, abstract: str, abstract_index: int, categories: List[str], level: str, method_json_output, abstract_chain_output, abstract_summary_output, parent_category=None):
        self.logger.info(f"Classifying abstract at {level} level")
        
        prompt_variables: Dict[str, Any] = {
            "abstract": abstract,
            "categories": categories,
            "method_json_output": json.dumps(method_json_output),
            "abstract_chain_output": json.dumps(abstract_chain_output),
            "abstract_summary_output": json.dumps(abstract_summary_output),
            "method_json_format": METHOD_JSON_FORMAT,
            "sentence_analysis_json_example": SENTENCE_ANALYSIS_JSON_EXAMPLE,
            "json_structure": SUMMARY_JSON_STRUCTURE,
            "json_classification_format": self.get_json_classification_form(),
            "categories_list_2": categories,
            "taxonomy_example": TAXONOMY_EXAMPLE,
        }
        
        try:
            classification_output: str = self.classification_chain_manager.run(prompt_variables)
            self.logger.info(f"Raw classification output: {classification_output}")
            
            if isinstance(classification_output, str):
                classification_output = json.loads(classification_output)
            
            classification_output: ClassificationOutput = ClassificationOutput(**classification_output)
            
        except Exception as e:
            self.logger.error(f"Error during classification: {e}")
            self.logger.error(f"Raw output: {classification_output}")
            return {}

        self.raw_classification_outputs.append(classification_output.model_dump())

        classified_categories: List[str] = self.extract_classified_categories(classification_output)
        self.logger.info(f"Classified categories at {level} level: {classified_categories}")

        result: Dict[str, Any] = {}
        for category in classified_categories:
            if level == "top":
                subcategories: List[str] = self.taxonomy.get_mid_categories(category)
                next_level: str = "mid"
            elif level == "mid":
                subcategories: List[str] = self.taxonomy.get_low_categories(parent_category, category)
                next_level: str = "low"
            else:
                subcategories: List[str] = []
                next_level: str = None

            if subcategories:
                result[category] = self.classify_abstract(
                    abstract, abstract_index, subcategories, next_level,
                    method_json_output, abstract_chain_output, abstract_summary_output, category
                )
            else:
                result[category] = {}

        if level == "top":
            self.classification_results[f"abstract_{abstract_index}"] = result

        return result

    # Process all themes
    def process_all_themes(self):
        self.logger.info("Processing themes for all abstracts")
        self.create_theme_chain()
        for i, abstract in enumerate(self.abstracts):
            self.logger.info(f"Processing themes for abstract {i+1}")
            if self.is_test_run:
                method_json_output, abstract_chain_output, abstract_summary_output = self._get_json_outputs(i)
            else:
                method_json_output, abstract_chain_output, abstract_summary_output = self.pre_classification_results.get(i)
                if method_json_output == None or abstract_chain_output == None or abstract_summary_output == None:
                    self.logger.warning(f"Pre-classification results for abstract {i} are not available, will be entered as null values")
                method_json_output = method_json_output if method_json_output != None else ""
                abstract_chain_output = abstract_chain_output if abstract_chain_output != None else ""
                abstract_summary_output = abstract_summary_output if abstract_summary_output != None else ""
            
            prompt_variables: Dict[str, Any] = {
                "abstract": abstract,
                "methodologies": json.dumps(method_json_output),
                "abstract_sentence_analysis": json.dumps(abstract_chain_output),
                "abstract_summary": json.dumps(abstract_summary_output),
                "categories": json.dumps(self.classification_results[f"abstract_{i}"]),
                "method_json_format": METHOD_JSON_FORMAT,
                "sentence_analysis_json_example": SENTENCE_ANALYSIS_JSON_EXAMPLE,
                "json_structure": SUMMARY_JSON_STRUCTURE,
                "theme_recognition_json_format": THEME_RECOGNITION_JSON_FORMAT
            }
            
            try:
                theme_output: str = self.theme_chain_manager.run(prompt_variables)
                self.logger.info(f"Raw theme output: {theme_output}")
                
                theme_output = json.loads(theme_output)
                
                self.raw_theme_outputs[f"abstract_{i}"] = theme_output
                
                # Extract themes
                themes: List[str] = theme_output.get("themes", [])
                self.classification_results[f"abstract_{i}"]["themes"] = themes
                
                # Update category themes
                # self.update_category_themes(categories, all_themes)
                
                self.logger.info(f"Processed themes for abstract {i+1}")
                
            except Exception as e:
                self.logger.error(f"Error during theme processing for abstract {i+1}: {e}")
                self.logger.error(f"Raw output: {theme_output}")

        self.logger.info("Completed theme processing for all abstracts")
            
    # Extract classified categories
    def extract_classified_categories(self, classification_output: ClassificationOutput) -> List[str]:
        self.logger.info("Extracting classified categories")
        categories: List[str] = [cat for classification in classification_output.classifications for cat in classification.categories]
        self.logger.info("Extracted classified categories")
        return categories

    # Get JSON classification form
    def get_json_classification_form(self) -> str:
        self.logger.info("Returning JSON classification form")
        return """
        {
            "classifications": [
                {
                    "abstract": "<abstract>",
                    "categories": [
                        "<first category you decided to classify the abstract into>",
                        "<second category you decided to classify the abstract into>"
                    ],
                    "reasoning": "<reasoning for the classification>",
                    "confidence_score": <confidence score float value between 0 and 1>
                }
            ],
            "reflection": "<reflection on parts you struggled with and why, and what could help alleviate that>",
            "feedback": [
                {
                    "assistant_name": "<name of the assistant you are providing feedback to>",
                    "feedback": "<feedback for the assistant>"
                }
            ]
        }
        """

    # Classify abstracts
    def classify(self):
        self.create_classification_chain()
        for i, abstract in enumerate(self.abstracts):
            self.logger.info(f"Processing abstract {i+1} of {len(self.abstracts)}")
            if self.is_test_run:
                method_json_output, abstract_chain_output, abstract_summary_output = self._get_json_outputs(i)
            else:
                self.run_pre_classification_chains()
                method_json_output, abstract_chain_output, abstract_summary_output = self.pre_classification_results.get(i)
                if method_json_output == None or abstract_chain_output == None or abstract_summary_output == None:
                    self.logger.warning(f"Pre-classification results for abstract {i} are not available, will be entered as null values")
                method_json_output = method_json_output if method_json_output != None else ""
                abstract_chain_output = abstract_chain_output if abstract_chain_output != None else ""
                abstract_summary_output = abstract_summary_output if abstract_summary_output != None else ""
                
            self.classify_abstract(
                abstract, i, self.taxonomy.get_top_categories(), "top",
                method_json_output, abstract_chain_output, abstract_summary_output
            )
            self.logger.info(f"Completed classification for abstract {i+1}")
            self.logger.info(f"Current classification results: {self.classification_results}")
        
        self.process_all_themes()

    # Get JSON outputs
    def _get_json_outputs(self, index):
        self.logger.info(f"Getting JSON outputs for abstract {index}")
        base_path: str = os.path.dirname(os.path.abspath(__file__))
        data_dir: str = os.path.join(base_path, "..", "..", "data")
        other_dir: str = os.path.join(data_dir, "other")
        ai_tests_dir: str = os.path.join(other_dir, "ai_tests")
        method_extraction_dir: str = os.path.join(ai_tests_dir, "method_extraction")
        sentence_analysis_dir: str = os.path.join(ai_tests_dir, "sentence_analysis")
        summary_dir: str = os.path.join(ai_tests_dir, "summary")

        with open(os.path.join(method_extraction_dir, f"method_json_output_{index}.json"), "r") as f:
            method_json_output: Dict[str, Any] = json.load(f)
        
        with open(os.path.join(sentence_analysis_dir, f"abstract_chain_output_{index}.json"), "r") as f:
            abstract_chain_output: Dict[str, Any] = json.load(f)
        
        with open(os.path.join(summary_dir, f"summary_chain_output_{index}.json"), "r") as f:
            abstract_summary_output: Dict[str, Any] = json.load(f)

        self.logger.info(f"Got JSON outputs for abstract {index}")
        return method_json_output, abstract_chain_output, abstract_summary_output

    # Save classification results
    def save_classification_results(self, output_path: str):
        self.logger.info("Saving classification results")
        
        if not self.is_test_run:
            with open(output_path, "w") as f:
                json.dump(self.classification_results, f, indent=4)
        else:
            base_path: str = os.path.dirname(os.path.abspath(__file__))
            data_dir: str = os.path.join(base_path, "..", "..", "data")
            other_dir: str = os.path.join(data_dir, "other")
            ai_tests_dir: str = os.path.join(other_dir, "ai_tests")
            classification_results_dir: str = os.path.join(ai_tests_dir, "classification_results")

            os.makedirs(classification_results_dir, exist_ok=True)
            
            with open(os.path.join(classification_results_dir, f"classification_results.json"), "w") as f:
                json.dump(self.classification_results, f, indent=4)

    # Get raw classification outputs
    def get_raw_classification_outputs(self):
        self.logger.info("Getting raw classification outputs")
        return self.raw_classification_outputs

    # Get raw theme results
    def get_raw_theme_results(self):
        self.logger.info("Getting raw theme results")
        return self.raw_theme_outputs
    
    # Save raw classification results
    def save_raw_classification_results(self, output_path: str):
        self.logger.info("Saving classification results")
        
        if not self.is_test_run:
            with open(output_path, "w") as f:
                json.dump(self.raw_classification_outputs, f, indent=4)
        else:
            base_path: str = os.path.dirname(os.path.abspath(__file__))
            data_dir: str = os.path.join(base_path, "..", "..", "data")
            other_dir: str = os.path.join(data_dir, "other")
            ai_tests_dir: str = os.path.join(other_dir, "ai_tests")
            raw_classification_dir: str = os.path.join(ai_tests_dir, "raw_classification_outputs")
            
            os.makedirs(raw_classification_dir, exist_ok=True)
            
            with open(os.path.join(raw_classification_dir, f"raw_classification_outputs.json"), "w") as f:
                json.dump(self.raw_classification_outputs, f, indent=4)
            
    # Save raw theme results
    def save_raw_theme_results(self, output_path: str):
        self.logger.info("Saving theme results")
        
        if not self.is_test_run:
            with open(output_path, "w") as f:
                json.dump(self.raw_theme_outputs, f, indent=4)
        else:
            base_path: str = os.path.dirname(os.path.abspath(__file__))
            data_dir: str = os.path.join(base_path, "..", "..", "data")
            other_dir: str = os.path.join(data_dir, "other")
            ai_tests_dir: str = os.path.join(other_dir, "ai_tests")
            raw_theme_dir: str = os.path.join(ai_tests_dir, "raw_theme_outputs")

            os.makedirs(raw_theme_dir, exist_ok=True)
            
            with open(os.path.join(raw_theme_dir, f"raw_theme_outputs.json"), "w") as f:
                json.dump(self.raw_theme_outputs, f, indent=4)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info("Starting classification process")
    from academic_metrics.AI.abstracts import abstracts

    try:
        taxonomy = Taxonomy()
        classifier = AbstractClassifier(taxonomy=taxonomy, abstracts=abstracts)
        logger.info("Classifier initialized")
        classifier.classify()
        logger.info("Classification completed")
        classifier.save_classification_results("outputs/classification_results.json")
        classifier.save_raw_theme_results("outputs/theme_results.json")
        classifier.save_raw_classification_results("outputs/raw_classification_outputs.json")
        logger.info("Classification results saved")
    except Exception as e:
        logger.error(f"Error during classification: {e}")