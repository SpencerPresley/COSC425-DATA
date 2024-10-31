import os
import json
import logging
from typing import List, Dict
from dotenv import load_dotenv
from academic_metrics.utils.taxonomy_util import Taxonomy
from academic_metrics.ChainBuilder import ChainManager
from academic_metrics.ai_prompts import (
    TopClassificationOutput, 
    method_json_format, 
    sentence_analysis_json_example, 
    json_structure, 
    taxonomy_example, 
    top_classification_system_message, 
    human_message_prompt, 
    ThemeAnalysis, 
    theme_recognition_json_format, 
    theme_recognition_system_message,
)

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
        extract_classified_categories(self, classification_output: TopClassificationOutput) -> List[str]:
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
    def __init__(self, taxonomy, abstracts: List[str]):  
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(logging.StreamHandler())
        self.logger.info("Initializing AbstractClassifier")
        self.taxonomy = taxonomy
        self.abstracts = abstracts
        self.logger.info("Initialized taxonomy and abstracts")
        self.classification_results = {f"abstract_{i}": {} for i in range(len(abstracts))}
        self.logger.info("Initialized classification results")
        self.raw_classification_outputs = []
        self.raw_theme_outputs = {f"abstract_{i}": {} for i in range(len(abstracts))}
        self.category_themes = {}
        self._load_env()
        self.classification_chain_manager = self._initialize_chain_manager()
        self.logger.info("Initialized classification chain manager")
        self.theme_chain_manager = self._initialize_chain_manager()
        self.logger.info("Initialized theme chain manager")
        
    def _load_env(self):
        return load_dotenv()

    def _initialize_chain_manager(self):
        api_key = os.getenv("OPENAI_API_KEY")
        return ChainManager(llm_model="gpt-4o-mini", api_key=api_key, llm_temperature=0.7)

    def create_classification_chain(self):
        self.classification_chain_manager.add_chain_layer(
            system_prompt=top_classification_system_message,
            human_prompt=human_message_prompt,
            parser_type="pydantic",
            return_type="json",
            pydantic_output_model=TopClassificationOutput,
            ignore_output_passthrough_key_name_error=True
        )
        
    def create_theme_chain(self):
        self.theme_chain_manager.add_chain_layer(
            system_prompt=theme_recognition_system_message,
            human_prompt=human_message_prompt,
            parser_type="pydantic",
            return_type="json",
            pydantic_output_model=ThemeAnalysis,
            ignore_output_passthrough_key_name_error=True
        )
        
    def get_themes_for_categories(self, categories: List[str]) -> List[str]:
        themes = set()
        for category in categories:
            themes.update(self.category_themes.get(category, []))
        return list(themes)
      
    def update_category_themes(self, categories: List[str], new_themes: List[str]):
        for category in categories:
            if category not in self.category_themes:
                self.category_themes[category] = set()
            self.category_themes[category].update(new_themes)
    
    def get_categories_for_abstract(self, abstract_index: int) -> List[str]:
        categories = []
        abstract_result = self.classification_results.get(f"abstract_{abstract_index}", {})
        
        def extract_categories(result, prefix=''):
            for key, value in result.items():
                full_category = f"{prefix}{key}" if prefix else key
                categories.append(full_category)
                if isinstance(value, dict):
                    extract_categories(value, f"{full_category}/")

        extract_categories(abstract_result)
        return categories
    
    def classify_abstract(self, abstract: str, abstract_index: int, categories: List[str], level: str, method_json_output, abstract_chain_output, abstract_summary_output, parent_category=None):
        self.logger.info(f"Classifying abstract at {level} level")
        
        prompt_variables = {
            "abstract": abstract,
            "categories": categories,
            "method_json_output": json.dumps(method_json_output),
            "abstract_chain_output": json.dumps(abstract_chain_output),
            "abstract_summary_output": json.dumps(abstract_summary_output),
            "method_json_format": method_json_format,
            "sentence_analysis_json_example": sentence_analysis_json_example,
            "json_structure": json_structure,
            "json_classification_format": self.get_json_classification_form(),
            "categories_list_2": categories,
            "taxonomy_example": taxonomy_example,
        }
        
        try:
            classification_output = self.classification_chain_manager.run(prompt_variables)
            self.logger.info(f"Raw classification output: {classification_output}")
            
            if isinstance(classification_output, str):
                classification_output = json.loads(classification_output)
            
            classification_output = TopClassificationOutput(**classification_output)
        except Exception as e:
            self.logger.error(f"Error during classification: {e}")
            self.logger.error(f"Raw output: {classification_output}")
            return {}

        self.raw_classification_outputs.append(classification_output.model_dump())

        classified_categories = self.extract_classified_categories(classification_output)
        self.logger.info(f"Classified categories at {level} level: {classified_categories}")

        result = {}
        for category in classified_categories:
            if level == "top":
                subcategories = self.taxonomy.get_mid_categories(category)
                next_level = "mid"
            elif level == "mid":
                subcategories = self.taxonomy.get_low_categories(parent_category, category)
                next_level = "low"
            else:
                subcategories = []
                next_level = None

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

    def process_all_themes(self):
        self.logger.info("Processing themes for all abstracts")
        self.create_theme_chain()
        for i, abstract in enumerate(self.abstracts):
            self.logger.info(f"Processing themes for abstract {i+1}")
            method_json_output, abstract_chain_output, abstract_summary_output = self._get_json_outputs(i)
            
            # categories = self.get_categories_for_abstract(i)
            # existing_themes = self.get_themes_for_categories(categories)
            
            prompt_variables = {
                "abstract": abstract,
                "methodologies": json.dumps(method_json_output),
                "abstract_sentence_analysis": json.dumps(abstract_chain_output),
                "abstract_summary": json.dumps(abstract_summary_output),
                "categories": json.dumps(self.classification_results[f"abstract_{i}"]),
                "method_json_format": method_json_format,
                "sentence_analysis_json_example": sentence_analysis_json_example,
                "json_structure": json_structure,
                "theme_recognition_json_format": theme_recognition_json_format
            }
            
            try:
                theme_output = self.theme_chain_manager.run(prompt_variables)
                self.logger.info(f"Raw theme output: {theme_output}")
                
                theme_output = json.loads(theme_output)
                
                self.raw_theme_outputs[f"abstract_{i}"] = theme_output
                
                # Extract themes
                themes = theme_output.get("themes", [])
                self.classification_results[f"abstract_{i}"]["themes"] = themes
                
                # Update category themes
                # self.update_category_themes(categories, all_themes)
                
                self.logger.info(f"Processed themes for abstract {i+1}")
                
            except Exception as e:
                self.logger.error(f"Error during theme processing for abstract {i+1}: {e}")
                self.logger.error(f"Raw output: {theme_output}")

        self.logger.info("Completed theme processing for all abstracts")
            
    def extract_classified_categories(self, classification_output: TopClassificationOutput) -> List[str]:
        self.logger.info("Extracting classified categories")
        categories = [cat for classification in classification_output.classifications for cat in classification.categories]
        self.logger.info("Extracted classified categories")
        return categories

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

    def classify(self):
        self.create_classification_chain()
        for i, abstract in enumerate(self.abstracts):
            self.logger.info(f"Processing abstract {i+1} of {len(self.abstracts)}")
            method_json_output, abstract_chain_output, abstract_summary_output = self._get_json_outputs(i)
            self.classify_abstract(
                abstract, i, self.taxonomy.get_top_categories(), "top",
                method_json_output, abstract_chain_output, abstract_summary_output
            )
            self.logger.info(f"Completed classification for abstract {i+1}")
            self.logger.info(f"Current classification results: {self.classification_results}")
        
        self.process_all_themes()

    def _get_json_outputs(self, index):
        self.logger.info(f"Getting JSON outputs for abstract {index}")
        base_path = os.path.dirname(os.path.abspath(__file__))
        \
        with open(os.path.join(base_path, f"outputs/method_extraction/method_json_output_{index}.json"), "r") as f:
            method_json_output = json.load(f)
        
        with open(os.path.join(base_path, f"outputs/sentence_analysis/abstract_chain_output_{index}.json"), "r") as f:
            abstract_chain_output = json.load(f)
        
        with open(os.path.join(base_path, f"outputs/summary/summary_chain_output_{index}.json"), "r") as f:
            abstract_summary_output = json.load(f)

        self.logger.info(f"Got JSON outputs for abstract {index}")
        return method_json_output, abstract_chain_output, abstract_summary_output

    def save_classification_results(self, output_path: str):
        self.logger.info("Saving classification results")
        with open(output_path, "w") as f:
            json.dump(self.classification_results, f, indent=4)

    def get_raw_classification_outputs(self):
        self.logger.info("Getting raw classification outputs")
        return self.raw_classification_outputs

    def get_raw_theme_results(self):
        self.logger.info("Getting raw theme results")
        return self.raw_theme_outputs
    
    def save_raw_classification_results(self, output_path: str):
        self.logger.info("Saving classification results")
        with open(output_path, "w") as f:
            json.dump(self.raw_classification_outputs, f, indent=4)
            
    def save_raw_theme_results(self, output_path: str):
        self.logger.info("Saving theme results")
        with open(output_path, "w") as f:
            json.dump(self.raw_theme_outputs, f, indent=4)

if __name__ == "__main__":
    # ! THIS FILE CAN BE RUN IN ISOLATION FOR TESTING 
    # ! IT WILL RUN THE 4 ABSTRACTS DEFINED IN PythonCode/academic_metrics/AI/abstract.py
    # ! OUTPUT FILES WILL BE SAVED TO THE PythonCode/academic_metrics/AI/outputs DIRECTORY
    # TODO: Move outputs to data/other/ai_outputs/classification_tests/
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info("Starting classification process")
    from academic_metrics.AI import abstracts

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