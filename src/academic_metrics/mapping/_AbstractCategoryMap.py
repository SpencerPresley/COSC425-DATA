import json
import os

from academic_metrics.enums import AttributeTypes
from academic_metrics.utils import Utilities, WarningManager


class AbstractCategoryMap:
    """
    A class for mapping abstracts to their corresponding categories.

    This class processes a directory of files, extracting abstracts, categories, and titles
    from each file, and creates a mapping between them. The results are stored in a JSON file.

    Attributes:
        utilities (Utilities): An instance of the Utilities class for various utility operations.
        warning_manager (WarningManager): An instance of WarningManager for handling warnings.
        dir_path (str): The directory path containing the files to be processed.
        results (dict): A dictionary storing the mapping of titles to abstracts and categories.

    Methods:
        map_abstract_categories: Processes files in the directory to create the abstract-category mapping.
        write_json: Writes the results to a JSON file.

    Design:
        Uses utility methods to read files and extract attributes.
        Implements a mapping process to associate abstracts with their categories and titles.
        Stores results in a structured dictionary format.

    Summary:
        Provides functionality to create a mapping between abstracts, categories, and titles
        from a set of files, and stores this mapping in a JSON format.
    """

    def __init__(
        self,
        *,
        utilities_obj: Utilities,
        warning_manager: WarningManager,
        dir_path: str,
        crossref_bool: bool,
    ):
        """
        Initializes the AbstractCategoryMap instance.

        This constructor sets up the necessary components and initiates the mapping process.

        Args:
            utilities_obj (Utilities): An instance of the Utilities class.
            warning_manager (WarningManager): An instance of WarningManager for handling warnings.
            dir_path (str): The directory path containing the files to be processed.
            crossref_bool (bool): A boolean indicating whether to use Crossref data (currently unused).

        Returns:
            None

        Design:
            Initializes class attributes with provided arguments.
            Calls map_abstract_categories to process the files and create the mapping.
            Writes the results to a JSON file.

        Summary:
            Sets up the AbstractCategoryMap instance and performs the initial mapping process.
        """
        self.utilities = utilities_obj
        self.warning_manager = warning_manager
        self.dir_path = dir_path
        self.results = self.map_abstract_categories(dir_path=self.dir_path)
        self.write_json("abstracts_to_categories.json", self.results)

    def map_abstract_categories(self, *, dir_path: str):
        """
        Maps abstracts to their corresponding categories and titles.

        This method processes each file in the specified directory, extracting
        abstracts, categories, and titles, and creates a mapping between them.

        Args:
            dir_path (str): The directory path containing the files to be processed.

        Returns:
            dict: A dictionary where keys are titles and values are dictionaries
                  containing the abstract and categories for each title.

        Design:
            Iterates through files in the specified directory.
            Uses utility methods to extract relevant attributes from each file.
            Creates a structured dictionary mapping titles to abstracts and categories.

        Summary:
            Processes files to create a mapping of titles to their abstracts and categories.
        """
        results = {}
        for filename in os.listdir(dir_path):
            file_path = os.path.join(dir_path, filename)
            if not os.path.isfile(file_path):
                continue

            file_content = self.file_ops.read_file(file_path)
            attributes = self.utilities.get_attributes(
                file_content,
                [
                    AttributeTypes.ABSTRACT,
                    AttributeTypes.WC_PATTERN,
                    AttributeTypes.TITLE,
                ],
            )

            abstract = (
                attributes[AttributeTypes.ABSTRACT][1]
                if attributes[AttributeTypes.ABSTRACT][0]
                else None
            )
            categories = (
                attributes[AttributeTypes.WC_PATTERN][1]
                if attributes[AttributeTypes.WC_PATTERN][0]
                else []
            )
            title = (
                attributes[AttributeTypes.TITLE][1]
                if attributes[AttributeTypes.TITLE][0]
                else None
            )

            if abstract:
                results[title] = {"abstract": abstract, "categories": categories}

        return results

    def write_json(self, filename: str, data: dict):
        """
        Writes the provided data to a JSON file.

        This method serializes the given dictionary data into a JSON format
        and writes it to a file with the specified filename.

        Args:
            filename (str): The name of the file to write the JSON data to.
            data (dict): The dictionary data to be written to the JSON file.

        Returns:
            None
        """
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)
