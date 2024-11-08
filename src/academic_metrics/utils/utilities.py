from __future__ import annotations

import os
import json
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from academic_metrics.enums import AttributeTypes

class Utilities:
    """
    A class containing various utility methods for processing and analyzing academic data.

    Attributes:
        strategy_factory (StrategyFactory): An instance of the StrategyFactory class.
        warning_manager (WarningManager): An instance of the WarningManager class.

    Methods:
        get_attributes(self, data, attributes):
            Extracts specified attributes from the data and returns them in a dictionary.
        crossref_file_splitter(self, *, path_to_file, split_files_dir_path):
            Splits a crossref file into individual entries and creates a separate file for each entry in the specified output directory.
        make_files(self, *, path_to_file: str, split_files_dir_path: str):
            Splits a document into individual entries and creates a separate file for each entry in the specified output directory.
    """
    CROSSREF_FILE_NAME_SUFFIX = "_crossref_item.json"
    
    def __init__(self, *, strategy_factory, warning_manager):
        """
        Initializes the Utilities class with the provided strategy factory and warning manager.

        Parameters:
            strategy_factory (StrategyFactory): An instance of the StrategyFactory class.
            warning_manager (WarningManager): An instance of the WarningManager class.
        """
        self.strategy_factory = strategy_factory
        self.warning_manager = warning_manager

    def get_attributes(self, data, attributes: List[AttributeTypes]):
        """
        Extracts specified attributes from the article entry and returns them in a dictionary.
        It also warns about missing or invalid attributes.

        Parameters:
            entry_text (str): The text of the article entry.
            attributes (list of str): A list of attribute names to extract from the entry, e.g., ["title", "author"].

        Returns:
            dict: A dictionary where keys are attribute names and values are tuples.
                  Each tuple contains a boolean indicating success or failure of extraction,
                  and the extracted attribute value or None.

        Raises:
            ValueError: If an attribute not defined in `self.attribute_patterns` is requested.
        """
        attribute_results = {}
        for attribute in attributes:
            extraction_strategy = self.strategy_factory.get_strategy(
                attribute, self.warning_manager
            )
            attribute_results[attribute] = extraction_strategy.extract_attribute(
                data
            )
        return attribute_results

    def crossref_file_splitter(self, *, path_to_file, split_files_dir_path):
        """
        Splits a crossref file into individual entries and creates a separate file for each entry in the specified output directory.

        Parameters:
            path_to_file (str): The path to the full json file containing all crossref objects to be split
            split_files_dir_path (str): The path to the directory where the individual crossref object files should be saved.

        Returns:
            list: A list of file names.
        """
        with open(path_to_file, "r") as f:
            data = json.load(f)

        for i, item in enumerate(data):
            file_name = f"{i}{self.CROSSREF_FILE_NAME_SUFFIX}"
            path = os.path.join(split_files_dir_path, file_name)

            if not os.path.exists(split_files_dir_path):
                os.makedirs(split_files_dir_path, exist_ok=True)

            with open(path, "w") as f:
                json.dump(item, f, indent=4)

        files = os.listdir(split_files_dir_path)
        return files

    def make_files(
        self,
        *,
        path_to_file: str,
        split_files_dir_path: str,
    ):
        """
        Splits a document into individual entries and creates a separate file for each entry in the specified output directory.

        Parameters:
            path_to_file (str): The path to the full text file containing all metadata for the entries.
            output_dir (str): The path to the directory where the individual entry files should be saved.

        Returns:
            file_paths: A dictionary where each key is the number of the entry (starting from 1) and each value is the path to the corresponding file.

        This method first splits the document into individual entries using the `splitter` method.
        It then iterates over each entry, extracts the necessary attributes to form a filename,
        ensures the output directory exists, and writes each entry's content to a new file in the output directory.
        Then returns the file_paths dictionary to make referencing any specific document later easier
        """
        return self.crossref_file_splitter(
            path_to_file=path_to_file, 
            split_files_dir_path=split_files_dir_path
        )