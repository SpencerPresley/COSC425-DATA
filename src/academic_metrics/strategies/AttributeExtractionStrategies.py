from __future__ import annotations

import json
import logging
import os
import re
import uuid
from abc import ABC, abstractmethod
from html import unescape
from typing import Any, Dict, List

from bs4 import BeautifulSoup

from academic_metrics.constants import LOG_DIR_PATH
from academic_metrics.enums import AttributeTypes
from academic_metrics.utils import WarningManager

from academic_metrics.factories import StrategyFactory


class AttributeExtractionStrategy(ABC):
    """
    Abstract base class for attribute extraction strategies.

    This class provides a framework for extracting various attributes from academic publication data.
    It defines common methods and properties that all specific extraction strategies should implement or utilize.

    It implements the Strategy pattern, allowing for flexible implementation of different extraction methods for different types of attributes or data sources. See more on the Strategy pattern here: https://en.wikipedia.org/wiki/Strategy_pattern

    Attributes:
        logger (logging.Logger): Logger for recording extraction-related events.
        abstract_pattern (re.Pattern): Regular expression pattern for extracting abstracts.
        missing_abstracts_file (str): File path for storing information about missing abstracts.
        warning_manager (WarningManager): Manages and logs warnings during extraction.
        unknown_authors_dict (dict): Stores information about unidentified authors.
        unknown_authors_file (str): File path for storing information about unknown authors.
        crossref_author_key (str): Key used to access author information in Crossref data.

    Methods:
        extract_attribute: Abstract method to be implemented by subclasses for specific attribute extraction.
        html_to_markdown: Converts HTML content to Markdown format.
        get_crossref_author_affils: Retrieves author affiliations from Crossref data.
        get_author_obj: Extracts author information from Crossref JSON data.
        set_author_sequence_dict: Organizes author information into a structured dictionary.
        write_missing_authors_file: Writes information about unknown authors to a file.
        create_author_sequence_dict: Creates a template dictionary for author sequence information.
        create_unknown_authors_dict: Creates a template dictionary for unknown authors.
        log_extraction_warning: Logs warnings encountered during attribute extraction.
        generate_error_id: Generates a unique identifier for error tracking.
        get_authors_as_list: Converts the author sequence dictionary to a list of author names.

    Design:
        This class is designed as an abstract base class, providing a common interface and shared functionality
        for various attribute extraction strategies. It uses the Strategy pattern, allowing for flexible
        implementation of different extraction methods for different types of attributes or data sources.

    Summary:
        The AttributeExtractionStrategy class serves as a foundation for creating specific attribute extraction
        strategies in an academic publication data processing system. It provides utility methods for handling
        common tasks such as HTML parsing, author information processing, and error logging, while defining
        an interface for implementing specific extraction logic in subclasses.
    """

    def __init__(
        self,
        warning_manager: WarningManager,
        missing_abstracts_file="missing_abstracts.txt",
    ):
        """
        Initializes the AttributeExtractionStrategy with necessary components and configurations.

        This constructor sets up the basic infrastructure needed for attribute extraction,
        including logging, file paths for storing missing data, and utilities for managing
        warnings and unknown author information.

        Args:
            warning_manager (WarningManager): An instance of WarningManager for handling and logging warnings
                                              encountered during the extraction process.
            missing_abstracts_file (str, optional): The file path where information about missing abstracts
                                                    will be stored. Defaults to "missing_abstracts.txt".

        Returns:
            None

        Design:
            The constructor initializes various attributes of the class, setting up the logger,
            compiling regular expressions, and preparing data structures for handling unknown
            authors and missing abstracts. It's designed to provide a consistent starting point
            for all subclasses of AttributeExtractionStrategy.

        Summary:
            This method prepares an instance of AttributeExtractionStrategy (or its subclass)
            for operation by setting up necessary tools and configurations for attribute extraction.
            It ensures that each strategy has access to logging, warning management, and file storage
            for handling edge cases and errors in the extraction process.
        """
        self.log_file_path: str = os.path.join(
            LOG_DIR_PATH, "attribute_extraction_strategies.log"
        )
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []
        if not self.logger.handlers:
            handler = logging.FileHandler(self.log_file_path)
            handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        self.abstract_pattern: re.Pattern = re.compile(r"AB\s(.+?)(?=\nC1)", re.DOTALL)
        self.missing_abstracts_file: str = missing_abstracts_file
        self.warning_manager: WarningManager = warning_manager
        self.unknown_authors_dict: dict = self.create_unknown_authors_dict()
        self.unknown_authors_file: str = "crossref_unknown_authors.json"
        self.crossref_author_key: str = "author"

    @abstractmethod
    def extract_attribute(self, entry_text: str) -> Any:
        """
        Abstract method to extract a specific attribute from the entry text.

        This method should be implemented by subclasses to define the specific
        extraction logic for each attribute type.

        Args:
            entry_text: The text or data from which to extract the attribute.
            entry_text applies to both WoS and Crossref data.

        Returns:
            The extracted attribute value.

        Raises:
            NotImplementedError: If the method is not implemented in a subclass.

        Design:
            This abstract method enforces a common interface for all attribute
            extraction strategies, allowing for polymorphic use of different
            strategies.

        Summary:
            Defines the contract for attribute extraction methods in subclasses.
        """
        raise NotImplementedError("This method must be implemented in a subclass")

    def html_to_markdown(self, html_content: str) -> str:
        """
        Converts HTML content to Markdown format.

        This method takes HTML content, particularly JATS XML, and converts it
        to a simplified Markdown format.

        Args:
            html_content (str): The HTML content to be converted.

        Returns:
            str: The converted content in Markdown format.

        Design:
            Uses BeautifulSoup for parsing HTML and custom logic to generate Markdown.
            Handles both sectioned and non-sectioned content.

        Summary:
            Transforms complex HTML/XML content into more readable Markdown format.
        """
        # Use BeautifulSoup to parse the HTML content
        soup: BeautifulSoup = BeautifulSoup(html_content, "lxml")

        markdown_content: list[str] = []

        # Check if there are any <jats:sec> sections
        sections: list[BeautifulSoup] = soup.find_all(["jats:sec", "section"])
        if sections:
            for section in sections:
                title = section.find("jats:title")
                if title:
                    string: str = f"## {title.get_text(strip=True)}:"
                    if title.get_text(strip=True).endswith(":"):
                        string = string[:-1]
                    markdown_content.append(string)

                paragraphs: list[BeautifulSoup] = section.find_all(["jats:p", "p"])
                for paragraph in paragraphs:
                    markdown_content.append(paragraph.get_text(strip=True) + "\n")
        else:
            # If no sections, combine all paragraphs
            paragraphs: list[BeautifulSoup] = soup.find_all(["jats:p", "p"])
            for paragraph in paragraphs:
                markdown_content.append(paragraph.get_text(strip=True) + "\n")

        return "\n".join(markdown_content)

    def get_crossref_author_affils(self, author_item: dict) -> list[str]:
        """
        Retrieves author affiliations from Crossref data.

        This method extracts the affiliation information for an author
        from the Crossref author data structure.

        It is designed to be used with Crossref data, not WoS data. It is NOT compatible with WoS data.

        This is implemented in the base class as it is used by more than a single subclass such as CrossrefAuthorExtractionStrategy and CrossrefDepartmentExtractionStrategy.

        Args:
            author_item (dict): A dictionary containing author information from Crossref.

        Returns:
            list[str]: A list of affiliation names for the author.

        Design:
            Directly accesses the 'affiliation' key in the author dictionary.
            Extracts the 'name' field from each affiliation entry.

        Summary:
            Extracts and returns a list of affiliation names for a given author.
        """
        raw_affils: list[str] = author_item["affiliation"]
        affils: list[str] = []
        for affil in raw_affils:
            affils.append(affil["name"])
        return affils

    def get_author_obj(self, *, crossref_json: dict) -> list[dict]:
        """
        Extracts the author object from Crossref JSON data.

        This method retrieves the author information from the Crossref JSON structure.
        It is designed to be used with Crossref data, not WoS data.

        Args:
            crossref_json (dict): The Crossref JSON data containing author information.

        Returns:
            list[dict]: A list of dictionaries, each containing information about an author.

        Design:
            Uses the class attribute 'crossref_author_key' to access author information.

        Summary:
            Extracts and returns the author object from Crossref JSON data.
        """
        authors: list[dict] = crossref_json.get(self.crossref_author_key, None)
        return authors

    def write_missing_authors_file(self, unknown_authors: dict) -> None:
        """
        Writes information about unknown authors to a file.

        This method saves the information about authors that couldn't be properly
        processed to a JSON file for later analysis.

        Args:
            unknown_authors (dict): A dictionary containing information about unknown authors.
            unknown_authors_file (str): The file path where the information will be saved.

        Returns:
            None

        Design:
            Uses JSON format to store the unknown authors information.

        Summary:
            Saves information about unknown or problematic authors to a file.
        """
        with open(self.missing_authors_file, "w") as unknown_authors_file:
            json.dump(unknown_authors, unknown_authors_file, indent=4)

    def create_author_sequence_dict(self) -> dict:
        """
        Creates a template dictionary for author sequence information.

        This method initializes a dictionary structure to store information
        about the first author and additional authors.

        Returns:
            dict: A dictionary with keys for 'first' author and 'additional' authors.

        Design:
            Provides a consistent structure for storing author information.

        Summary:
            Creates and returns a template dictionary for organizing author information.
        """
        return {"first": {"author_name": "", "affiliations": []}, "additional": []}

    def create_unknown_authors_dict(self) -> dict:
        """
        Creates a template dictionary for unknown authors.

        This method initializes a dictionary to store information about
        authors that couldn't be properly processed.

        Returns:
            dict: A dictionary with a key for 'unknown_authors'.

        Design:
            Provides a consistent structure for storing information about problematic authors.

        Summary:
            Creates and returns a template dictionary for tracking unknown authors.
        """
        return {"unknown_authors": []}

    def log_extraction_warning(
        self,
        attribute_class_name: str,
        warning_message: str,
        entry_id: str = None,
        line_prefix: str = None,
    ):
        """
        Logs warnings encountered during attribute extraction.

        This method creates a standardized log message for extraction warnings
        and can optionally include specific entry information.

        Args:
            attribute_class_name (str): The name of the attribute class where the warning occurred.
            warning_message (str): The specific warning message.
            entry_id (str, optional): An identifier for the entry causing the warning.
            line_prefix (str, optional): A prefix to identify specific lines in the entry.

        Returns:
            None

        Design:
            Generates a unique error ID for each warning.
            Commented-out code shows potential for more detailed logging.

        Summary:
            Creates and logs a standardized warning message for attribute extraction issues.
        """
        log_message = f"Failed to extract {attribute_class_name}. Error ID: {self.generate_error_id()}"
        self.logger.warning(log_message)
        self.warning_manager.log_warning(attribute_class_name, log_message, entry_id)

        # * Commented out code is potential for more detailed logging.
        # if type(entry_id) == str:
        #     for line in entry_id.splitlines():
        #         if line.startswith(line_prefix):
        #             log_message += f" - Line: {line}"
        # else:
        #     log_message += f" - Entry ID: {entry_id[:25]}"
        # log_message += f" - {warning_message}"
        # self.logger.warning(log_message)
        # self.warning_manager.log_warning(attribute_class_name, log_message, entry_id)

    def generate_error_id(self) -> str:
        """
        Generates a unique identifier for error tracking.

        This method creates a UUID to uniquely identify each error or warning instance.

        Returns:
            str: A unique UUID string.

        Design:
            Uses Python's uuid module to generate a version 4 UUID.

        Summary:
            Generates and returns a unique identifier string for error tracking purposes.
        """
        return str(uuid.uuid4())

    def write_missing_authors_file(
        self, unknown_authors: dict, unknown_authors_file: str
    ) -> None:
        """
        Converts the author sequence dictionary to a list of author names.

        This method extracts author names from the structured author sequence dictionary
        and returns them as a simple list.

        Args:
            author_sequence_dict (dict): A dictionary containing structured author information.

        Returns:
            list[str]: A list of author names in the order they appear in the publication.

        Design:
            Handles both the first author and additional authors from the dictionary.

        Summary:
            Extracts and returns a list of author names from the structured author dictionary.
        """
        with open(unknown_authors_file, "w") as unknown_authors_file:
            json.dump(unknown_authors, unknown_authors_file, indent=4)

    def set_author_sequence_dict(
        self, *, author_items: list[dict], author_sequence_dict: dict
    ) -> None:
        """
        Organizes author information into a structured dictionary.

        This method processes a list of author items and organizes them into a dictionary
        based on their sequence (first author or additional authors).
        It is designed to work with Crossref data, not WoS data.

        Args:
            author_items (list[dict]): A list of dictionaries containing author information.
            author_sequence_dict (dict): A dictionary to store the organized author information.

        Returns:
            None

        Design:
            Processes each author item, extracting name and affiliation information.
            Handles cases for first author and additional authors separately.
            Logs warnings for missing or incomplete author information.

        Summary:
            Organizes author information into a structured dictionary format.
        """
        for author_item in author_items:
            sequence: str = author_item.get("sequence", "")
            author_given_name: str = author_item.get("given", "")
            author_family_name: str = author_item.get("family", "")

            author_name: str = ""
            if author_given_name and author_family_name:
                author_name = f"{author_given_name} {author_family_name}"
            else:
                self.log_extraction_warning(
                    attribute_class_name=self.__class__.__name__,
                    warning_message="Attribute: 'Crossref_Author' was not found in the entry",
                    entry_id=author_item,
                )
                self.unknown_authors_dict["unknown_authors"].append(author_item)
                continue

            author_affiliations: list[str] = self.get_crossref_author_affils(
                author_item
            )

            if not sequence:
                self.log_extraction_warning(
                    attribute_class_name=self.__class__.__name__,
                    warning_message="Attribute: 'Crossref_Author' was not found in the entry",
                    entry_id=author_item,
                )
                self.unknown_authors_dict["unknown_authors"].append(
                    f"Error ID: {self.generate_error_id()} - {author_item}"
                )
                continue

            if sequence == "first":
                author_sequence_dict[sequence]["author_name"] = author_name
                for affiliation in author_affiliations:
                    author_sequence_dict[sequence]["affiliations"].append(affiliation)

            elif sequence == "additional":
                additional_author_dict: dict = {}
                additional_author_dict["author_name"] = author_name
                additional_author_dict["affiliations"] = []
                for affiliation in author_affiliations:
                    additional_author_dict["affiliations"].append(affiliation)
                author_sequence_dict["additional"].append(additional_author_dict)

        self.write_missing_authors_file(
            self.unknown_authors_dict, self.unknown_authors_file
        )

    def get_authors_as_list(self, *, author_sequence_dict: dict) -> list[str]:
        """
        Converts the author sequence dictionary to a list of author names.

        This method extracts author names from the structured author sequence dictionary
        and returns them as a simple list.

        Args:
            author_sequence_dict (dict): A dictionary containing structured author information.

        Returns:
            list[str]: A list of author names in the order they appear in the publication.

        Design:
            Handles both the first author and additional authors from the dictionary.

        Summary:
            Extracts and returns a list of author names from the structured author dictionary.
        """
        authors: list[str] = []
        authors.append(author_sequence_dict["first"]["author_name"])
        for item in author_sequence_dict["additional"]:
            authors.append(item["author_name"])
        return authors


@StrategyFactory.register_strategy(AttributeTypes.CROSSREF_TITLE)
class CrossrefTitleExtractionStrategy(AttributeExtractionStrategy):
    """
    A strategy for extracting title information from Crossref data.

    This class implements the AttributeExtractionStrategy for title extraction
    specifically from Crossref JSON data. It focuses on extracting and cleaning
    the title(s) of a publication.

    Attributes:
        title_key (str): The key used to access title information in the Crossref JSON.

    Methods:
        clean_title: Removes HTML tags from a title string.
        extract_attribute: Extracts and cleans the title(s) from the Crossref entry.

    Design:
        Utilizes BeautifulSoup for HTML tag removal and handles potential multiple titles.
        Implements the Strategy pattern for title extraction from Crossref data.

    Summary:
        Provides a specialized strategy for extracting and cleaning publication titles
        from Crossref data entries, handling potential HTML content and multiple titles.
    """

    def __init__(self, warning_manager: WarningManager):
        """
        Initializes the CrossrefTitleExtractionStrategy.

        This constructor sets up the strategy with a warning manager and defines
        the key for accessing title information in Crossref data.

        Args:
            warning_manager (WarningManager): An instance of WarningManager for handling extraction warnings.

        Returns:
            None

        Design:
            Calls the superclass constructor and sets up the title key for Crossref data.

        Summary:
            Prepares the strategy instance for title extraction from Crossref data.
        """
        super().__init__(warning_manager=warning_manager)
        self.log_file_path = LOG_DIR_PATH / "crossref_title_extraction_strategy.log"
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []
        if not self.logger.handlers:
            handler = logging.FileHandler(self.log_file_path)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            self.logger.addHandler(handler)
        self.title_key: str = "title"

    def clean_title(self, title: str) -> str:
        """
        Removes HTML tags from a title string using BeautifulSoup.

        This method uses BeautifulSoup to parse and remove any HTML tags
        present in the title string.

        Args:
            title (str): The title string potentially containing HTML tags.

        Returns:
            str: The cleaned title string with HTML tags removed.

        Design:
            Uses BeautifulSoup with 'html.parser' to safely remove HTML tags.

        Summary:
            Cleans a title string by removing any HTML tags it may contain.
        """
        soup: BeautifulSoup = BeautifulSoup(title, "html.parser")
        return soup.get_text()

    def extract_attribute(self, entry_text: dict) -> tuple[bool, list[str]]:
        """
        Extracts and cleans the title(s) from the Crossref entry.

        This method retrieves the title(s) from the Crossref JSON data,
        handles potential multiple titles, and cleans each title by removing HTML tags.

        Args:
            entry_text (dict): The Crossref JSON data containing the publication information.

        Returns:
            tuple[bool, list[str]]: A tuple containing:
                - A boolean indicating success (True) or failure (False) of the extraction.
                - A list of cleaned title strings, or None if no titles were found.

        Design:
            Retrieves titles using the predefined title_key.
            Handles cases where a single title or multiple titles may be present.
            Cleans each title using the clean_title method.
            Logs a warning if no titles are found.

        Summary:
            Extracts, cleans, and returns the publication title(s) from Crossref JSON data.
        """
        titles: list[str] = entry_text.get(self.title_key, [])
        if not isinstance(titles, list):
            titles = [titles]
        cleaned_titles: list[str] = [self.clean_title(title) for title in titles]
        if cleaned_titles:
            return (True, cleaned_titles)
        else:
            self.log_extraction_warning(
                attribute_class_name=self.__class__.__name__,
                warning_message="Attribute: 'Crossref_Title' was not found in the entry",
                entry_id=entry_text,
            )
            return (False, None)


@StrategyFactory.register_strategy(AttributeTypes.CROSSREF_ABSTRACT)
class CrossrefAbstractExtractionStrategy(AttributeExtractionStrategy):
    """
    A strategy for extracting abstract information from Crossref data.

    This class implements the AttributeExtractionStrategy for abstract extraction
    specifically from Crossref JSON data. It focuses on extracting and cleaning
    the abstract of a publication.

    Attributes:
        abstract_key (str): The key used to access abstract information in the Crossref JSON.

    Methods:
        clean_abstract: Converts HTML content in the abstract to Markdown format.
        extract_attribute: Extracts and cleans the abstract from the Crossref entry.

    Design:
        Utilizes the html_to_markdown method for cleaning HTML content in abstracts.
        Implements the Strategy pattern for abstract extraction from Crossref data.

    Summary:
        Provides a specialized strategy for extracting and cleaning publication abstracts
        from Crossref data entries, handling potential HTML content.
    """

    def __init__(self, warning_manager: WarningManager):
        """
        Initializes the CrossrefAbstractExtractionStrategy.

        This constructor sets up the strategy with a warning manager and defines
        the key for accessing abstract information in Crossref data.

        Args:
            warning_manager (WarningManager): An instance of WarningManager for handling extraction warnings.

        Returns:
            None

        Design:
            Calls the superclass constructor and sets up the abstract key for Crossref data.

        Summary:
            Prepares the strategy instance for abstract extraction from Crossref data.
        """
        super().__init__(warning_manager=warning_manager)
        self.log_file_path = LOG_DIR_PATH / "crossref_abstract_extraction_strategy.log"
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []
        if not self.logger.handlers:
            handler = logging.FileHandler(self.log_file_path)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            self.logger.addHandler(handler)
        self.abstract_key: str = "abstract"

    def clean_abstract(self, abstract: str) -> str:
        """
        Cleans the abstract by converting HTML content to Markdown format.

        This method uses the html_to_markdown method to convert any HTML content
        in the abstract to a more readable Markdown format.

        Args:
            abstract (str): The abstract string potentially containing HTML content.

        Returns:
            str: The cleaned abstract string in Markdown format.

        Design:
            Utilizes the html_to_markdown method inherited from the parent class.

        Summary:
            Converts HTML content in the abstract to Markdown for improved readability.
        """
        return self.html_to_markdown(abstract)

    def extract_attribute(self, entry_text: dict) -> tuple[bool, str]:
        """
        Extracts and cleans the abstract from the Crossref entry.

        This method retrieves the abstract from the Crossref JSON data,
        cleans it by converting HTML to Markdown, and returns the result.

        Args:
            entry_text (dict): The Crossref JSON data containing the publication information.

        Returns:
            tuple[bool, str]: A tuple containing:
                - A boolean indicating success (True) or failure (False) of the extraction.
                - The cleaned abstract string, or None if no abstract was found.

        Design:
            Retrieves the abstract using the predefined abstract_key.
            Cleans the abstract using the clean_abstract method.
            Logs a warning if no abstract is found.

        Summary:
            Extracts, cleans, and returns the publication abstract from Crossref JSON data.
        """
        abstract: str = entry_text.get(self.abstract_key, None)
        if abstract:
            abstract = self.clean_abstract(abstract)
            return (True, abstract)
        else:
            self.log_extraction_warning(
                attribute_class_name=self.__class__.__name__,
                warning_message="Attribute: 'Crossref_Abstract' was not found in the entry",
                entry_id=entry_text,
            )
            return (False, None)


@StrategyFactory.register_strategy(AttributeTypes.CROSSREF_AUTHORS)
class CrossrefAuthorExtractionStrategy(AttributeExtractionStrategy):
    """
    A strategy for extracting author information from Crossref data.

    This class implements the AttributeExtractionStrategy for author extraction
    specifically from Crossref JSON data. It focuses on extracting and organizing
    author names and handling cases where author information might be incomplete.

    Attributes:
        unknown_authors (dict): A dictionary to store information about authors with incomplete data.
        missing_authors_file (str): The file path to store information about unknown authors.

    Methods:
        get_author_name: Constructs a full author name from given and family name components.
        extract_attribute: Extracts and organizes author information from the Crossref entry.

    Design:
        Utilizes helper methods to process individual author items and organize them.
        Implements the Strategy pattern for author extraction from Crossref data.

    Summary:
        Provides a specialized strategy for extracting and organizing author information
        from Crossref data entries, handling potential incomplete author data.
    """

    def __init__(self, warning_manager: WarningManager):
        """
        Initializes the CrossrefAuthorExtractionStrategy.

        This constructor sets up the strategy with a warning manager and initializes
        structures for handling unknown authors.

        Args:
            warning_manager (WarningManager): An instance of WarningManager for handling extraction warnings.

        Returns:
            None

        Design:
            Calls the superclass constructor and sets up data structures for unknown authors.

        Summary:
            Prepares the strategy instance for author extraction from Crossref data.
        """
        super().__init__(warning_manager=warning_manager)
        self.log_file_path = LOG_DIR_PATH / "crossref_author_extraction_strategy.log"
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []
        if not self.logger.handlers:
            handler = logging.FileHandler(self.log_file_path)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            self.logger.addHandler(handler)
        self.unknown_authors: dict = self.create_unknown_authors_dict()
        self.missing_authors_file: str = "unknown_authors.json"

    def get_author_name(self, author_item: dict) -> str:
        """
        Constructs a full author name from given and family name components.

        This method attempts to create a full author name from the given and family
        name fields in the author item. If either component is missing, it logs a warning.

        Args:
            author_item (dict): A dictionary containing author information from Crossref.

        Returns:
            str: The full author name if both components are present, None otherwise.

        Design:
            Extracts given and family names from the author item.
            Logs a warning if either component is missing.

        Summary:
            Constructs and returns a full author name, or None if information is incomplete.
        """
        given_name: str = author_item.get("given", "")
        family_name: str = author_item.get("family", "")
        if given_name and family_name:
            return f"{given_name} {family_name}"
        else:
            self.log_extraction_warning(
                attribute_class_name=self.__class__.__name__,
                warning_message="Attribute: 'Crossref_Author' was not found in the entry",
                entry_id=author_item,
            )
            return None

    def extract_attribute(self, crossref_json: dict) -> tuple[bool, list[str]]:
        """
        Extracts and organizes author information from the Crossref entry.

        This method processes the Crossref JSON data to extract author information,
        organizes it into a structured format, and returns a list of author names.

        Args:
            crossref_json (dict): The Crossref JSON data containing the publication information.

        Returns:
            tuple[bool, list[str]]: A tuple containing:
                - A boolean indicating success (True) or failure (False) of the extraction.
                - A list of author names extracted from the Crossref data.

        Design:
            Uses helper methods to extract author objects and organize them into a sequence.
            Converts the organized author data into a simple list of names.

        Summary:
            Extracts, organizes, and returns a list of author names from Crossref JSON data.
        """
        author_items: list[dict] = self.get_author_obj(crossref_json=crossref_json)
        author_sequence_dict: dict = self.create_author_sequence_dict()
        self.set_author_sequence_dict(
            author_items=author_items,
            author_sequence_dict=author_sequence_dict,
        )
        return (
            True,
            self.get_authors_as_list(author_sequence_dict=author_sequence_dict),
        )


@StrategyFactory.register_strategy(AttributeTypes.CROSSREF_DEPARTMENTS)
class CrossrefDepartmentExtractionStrategy(AttributeExtractionStrategy):
    """
    A strategy for extracting department information from Crossref data.

    This class implements the AttributeExtractionStrategy for department extraction
    specifically from Crossref JSON data. It focuses on extracting and organizing
    department affiliations for each author in a publication.

    Methods:
        extract_attribute: Extracts and organizes department affiliations from the Crossref entry.

    Design:
        Utilizes helper methods to process author information and extract department affiliations.
        Implements the Strategy pattern for department extraction from Crossref data.

    Summary:
        Provides a specialized strategy for extracting and organizing department affiliations
        for authors from Crossref data entries.
    """

    def __init__(self, warning_manager: WarningManager):
        """
        Initializes the CrossrefDepartmentExtractionStrategy.

        This constructor sets up the strategy with a warning manager.

        Args:
            warning_manager (WarningManager): An instance of WarningManager for handling extraction warnings.

        Returns:
            None

        Design:
            Calls the superclass constructor to set up the warning manager.

        Summary:
            Prepares the strategy instance for department extraction from Crossref data.
        """
        super().__init__(warning_manager=warning_manager)
        self.log_file_path = (
            LOG_DIR_PATH / "crossref_department_extraction_strategy.log"
        )
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []
        if not self.logger.handlers:
            handler = logging.FileHandler(self.log_file_path)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            self.logger.addHandler(handler)

    def extract_attribute(self, crossref_json: dict) -> tuple[bool, list[str]]:
        """
        Extracts and organizes department affiliations from the Crossref entry.

        This method processes the Crossref JSON data to extract department affiliations
        for each author, organizing them into a dictionary structure.

        Args:
            crossref_json (dict): The Crossref JSON data containing the publication information.

        Returns:
            tuple[bool, dict[str, list[str]]]: A tuple containing:
                - A boolean indicating success (True) or failure (False) of the extraction.
                - A dictionary where keys are author names and values are lists of their affiliations.

        Design:
            Uses helper methods to extract author objects and organize them into a sequence.
            Processes both the first author and additional authors separately.
            Creates a dictionary mapping author names to their department affiliations.
            Logs a warning if no department affiliations are found.

        Summary:
            Extracts and returns a dictionary of author names mapped to their department affiliations
            from Crossref JSON data.
        """
        author_items: list[dict] = self.get_author_obj(crossref_json=crossref_json)
        sequence_dict: dict = self.create_author_sequence_dict()
        self.set_author_sequence_dict(
            author_items=author_items,
            author_sequence_dict=sequence_dict,
        )

        # keys are authors, values are their affiliation
        department_affiliations: dict[str, str] = {}
        first_author = sequence_dict.get("first", "")
        if first_author:
            department_affiliations[first_author.get("author_name", "Unknown")] = (
                first_author.get("affiliations", [])
            )

        additional_authors = sequence_dict.get("additional", [])
        if additional_authors:
            for author in additional_authors:
                department_affiliations[author.get("author_name", "")] = author.get(
                    "affiliations", []
                )
        if department_affiliations:
            return (True, department_affiliations)
        else:
            self.log_extraction_warning(
                attribute_class_name=self.__class__.__name__,
                warning_message="Attribute: 'Crossref_Department' was not found in the entry",
                entry_id=crossref_json,
            )
            return (False, None)


@StrategyFactory.register_strategy(AttributeTypes.CROSSREF_CATEGORIES)
class CrossrefCategoriesExtractionStrategy(AttributeExtractionStrategy):
    """
    A strategy for extracting category information from Crossref data.

    This class implements the AttributeExtractionStrategy for category extraction
    specifically from Crossref JSON data. It focuses on retrieving the categories
    associated with a publication.

    Methods:
        extract_attribute: Extracts the categories from the Crossref entry.

    Design:
        Implements the Strategy pattern for category extraction from Crossref data.
        Uses a simple dictionary lookup to retrieve category information.

    Summary:
        Provides a specialized strategy for extracting publication categories
        from Crossref data entries.
    """

    def __init__(self, warning_manager: WarningManager):
        """
        Initializes the CrossrefCategoriesExtractionStrategy.

        This constructor sets up the strategy with a warning manager.

        Args:
            warning_manager (WarningManager): An instance of WarningManager for handling extraction warnings.

        Returns:
            None

        Design:
            Calls the superclass constructor to set up the warning manager.

        Summary:
            Prepares the strategy instance for category extraction from Crossref data.
        """
        super().__init__(warning_manager=warning_manager)
        self.log_file_path = (
            LOG_DIR_PATH / "crossref_categories_extraction_strategy.log"
        )
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []
        if not self.logger.handlers:
            handler = logging.FileHandler(self.log_file_path)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            self.logger.addHandler(handler)

    def extract_attribute(self, crossref_json: dict) -> tuple[bool, list[str]]:
        """
        Extracts the categories from the Crossref entry.

        This method retrieves the categories associated with a publication
        from the Crossref JSON data.

        Args:
            crossref_json (dict): The Crossref JSON data containing the publication information.

        Returns:
            tuple[bool, list[str]]: A tuple containing:
                - A boolean indicating success (True) if categories are found, False otherwise.
                - A list of category strings, or None if no categories are found.

        Design:
            Uses a simple dictionary get method to retrieve the categories.
            Returns True only if categories are present.

        Summary:
            Extracts and returns the categories associated with a publication from Crossref JSON data.
        """
        top_level_categories = crossref_json.get("categories", {}).get("top", [])
        mid_level_categories = crossref_json.get("categories", {}).get("mid", [])
        low_level_categories = crossref_json.get("categories", {}).get("low", [])
        categories = {
            "top": top_level_categories,
            "mid": mid_level_categories,
            "low": low_level_categories,
        }

        return (True if categories else False, categories)


@StrategyFactory.register_strategy(AttributeTypes.CROSSREF_CITATION_COUNT)
class CrossrefCitationCountExtractionStrategy(AttributeExtractionStrategy):
    """
    A strategy for extracting citation count information from Crossref data.

    This class implements the AttributeExtractionStrategy for citation count extraction
    specifically from Crossref JSON data. It focuses on retrieving the number of times
    a publication has been cited.

    Methods:
        extract_attribute: Extracts the citation count from the Crossref entry.

    Design:
        Implements the Strategy pattern for citation count extraction from Crossref data.
        Uses a simple dictionary lookup to retrieve citation count information.

    Summary:
        Provides a specialized strategy for extracting publication citation counts
        from Crossref data entries.
    """

    def __init__(self, warning_manager: WarningManager):
        """
        Initializes the CrossrefCitationCountExtractionStrategy.

        This constructor sets up the strategy with a warning manager.

        Args:
            warning_manager (WarningManager): An instance of WarningManager for handling extraction warnings.

        Returns:
            None

        Design:
            Calls the superclass constructor to set up the warning manager.

        Summary:
            Prepares the strategy instance for citation count extraction from Crossref data.
        """
        super().__init__(warning_manager=warning_manager)
        self.log_file_path = (
            LOG_DIR_PATH / "crossref_citation_count_extraction_strategy.log"
        )
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []
        if not self.logger.handlers:
            handler = logging.FileHandler(self.log_file_path)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            self.logger.addHandler(handler)

    def extract_attribute(self, crossref_json: dict) -> tuple[bool, int]:
        """
        Extracts the citation count from the Crossref entry.

        This method retrieves the number of times a publication has been cited
        from the Crossref JSON data.

        Args:
            crossref_json (dict): The Crossref JSON data containing the publication information.

        Returns:
            tuple[bool, int]: A tuple containing:
                - A boolean always set to True (as the method always returns a count, even if it's 0).
                - An integer representing the citation count.

        Design:
            Uses a dictionary get method to retrieve the citation count, defaulting to 0 if not found.
            Always returns True as the first element of the tuple, as a count is always available.

        Summary:
            Extracts and returns the citation count for a publication from Crossref JSON data.
        """
        citation_count = crossref_json.get("is-referenced-by-count", 0)
        return (True, citation_count)


@StrategyFactory.register_strategy(AttributeTypes.CROSSREF_LICENSE_URL)
class CrossrefLicenseURLExtractionStrategy(AttributeExtractionStrategy):
    def __init__(self, warning_manager: WarningManager):
        super().__init__(warning_manager=warning_manager)
        self.log_file_path = (
            LOG_DIR_PATH / "crossref_license_url_extraction_strategy.log"
        )
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []
        if not self.logger.handlers:
            handler = logging.FileHandler(self.log_file_path)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            self.logger.addHandler(handler)

    def extract_attribute(self, entry_text: dict) -> tuple[bool, str]:
        license_info = entry_text.get("license", [])
        if license_info and isinstance(license_info, list):
            url = license_info[0].get("URL")
            if url:
                return (True, url)
        self.log_extraction_warning(
            attribute_class_name=self.__class__.__name__,
            warning_message="Attribute: 'Crossref_License_URL' was not found in the entry",
            entry_id=entry_text,
        )
        return (False, None)


@StrategyFactory.register_strategy(AttributeTypes.CROSSREF_PUBLISHED_PRINT)
class CrossrefPublishedPrintExtractionStrategy(AttributeExtractionStrategy):
    def __init__(self, warning_manager: WarningManager):
        super().__init__(warning_manager=warning_manager)
        self.log_file_path = (
            LOG_DIR_PATH / "crossref_published_print_extraction_strategy.log"
        )
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []
        if not self.logger.handlers:
            handler = logging.FileHandler(self.log_file_path)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            self.logger.addHandler(handler)

    def extract_attribute(self, entry_text: dict) -> tuple[bool, str]:
        published_print = entry_text.get("published-print", {}).get("date-parts", [[]])[
            0
        ]
        if published_print:
            date_str = "-".join(map(str, published_print))
            return (True, date_str)
        self.log_extraction_warning(
            attribute_class_name=self.__class__.__name__,
            warning_message="Attribute: 'Crossref_Published_Print' was not found in the entry",
            entry_id=entry_text,
        )
        return (False, None)


@StrategyFactory.register_strategy(AttributeTypes.CROSSREF_CREATED_DATE)
class CrossrefCreatedDateExtractionStrategy(AttributeExtractionStrategy):
    def __init__(self, warning_manager: WarningManager):
        super().__init__(warning_manager=warning_manager)
        self.log_file_path = (
            LOG_DIR_PATH / "crossref_created_date_extraction_strategy.log"
        )
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []
        if not self.logger.handlers:
            handler = logging.FileHandler(self.log_file_path)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            self.logger.addHandler(handler)

    def extract_attribute(self, entry_text: dict) -> tuple[bool, str]:
        created = entry_text.get("created", {}).get("date-time")
        if created:
            return (True, created)
        self.log_extraction_warning(
            attribute_class_name=self.__class__.__name__,
            warning_message="Attribute: 'Crossref_Created_Date' was not found in the entry",
            entry_id=entry_text,
        )
        return (False, None)


@StrategyFactory.register_strategy(AttributeTypes.CROSSREF_PUBLISHED_ONLINE)
class CrossrefPublishedOnlineExtractionStrategy(AttributeExtractionStrategy):
    def __init__(self, warning_manager: WarningManager):
        super().__init__(warning_manager=warning_manager)
        self.log_file_path = (
            LOG_DIR_PATH / "crossref_published_online_extraction_strategy.log"
        )
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []
        if not self.logger.handlers:
            handler = logging.FileHandler(self.log_file_path)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            self.logger.addHandler(handler)

    def extract_attribute(self, entry_text: dict) -> tuple[bool, str]:
        published_online = entry_text.get("published-online", {}).get(
            "date-parts", [[]]
        )[0]
        if published_online:
            date_str = "-".join(map(str, published_online))
            return (True, date_str)
        self.log_extraction_warning(
            attribute_class_name=self.__class__.__name__,
            warning_message="Attribute: 'Crossref_Published_Online' was not found in the entry",
            entry_id=entry_text,
        )
        return (False, None)


@StrategyFactory.register_strategy(AttributeTypes.CROSSREF_JOURNAL)
class CrossrefJournalExtractionStrategy(AttributeExtractionStrategy):
    def __init__(self, warning_manager: WarningManager):
        super().__init__(warning_manager=warning_manager)
        self.log_file_path = LOG_DIR_PATH / "crossref_journal_extraction_strategy.log"
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []
        if not self.logger.handlers:
            handler = logging.FileHandler(self.log_file_path)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            self.logger.addHandler(handler)

    def extract_attribute(self, entry_text: dict) -> tuple[bool, str]:
        journal = entry_text.get("container-title", [])
        if journal and isinstance(journal, list):
            return (True, journal[0])
        self.log_extraction_warning(
            attribute_class_name=self.__class__.__name__,
            warning_message="Attribute: 'Crossref_Journal' was not found in the entry",
            entry_id=entry_text,
        )
        return (False, None)


@StrategyFactory.register_strategy(AttributeTypes.CROSSREF_URL)
class CrossrefURLExtractionStrategy(AttributeExtractionStrategy):
    def __init__(self, warning_manager: WarningManager):
        super().__init__(warning_manager=warning_manager)
        self.log_file_path = LOG_DIR_PATH / "crossref_url_extraction_strategy.log"
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []
        if not self.logger.handlers:
            handler = logging.FileHandler(self.log_file_path)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            self.logger.addHandler(handler)

    def extract_attribute(self, entry_text: dict) -> tuple[bool, str]:
        url = entry_text.get("URL")
        if url:
            return (True, url)
        self.log_extraction_warning(
            attribute_class_name=self.__class__.__name__,
            warning_message="Attribute: 'Crossref_URL' was not found in the entry",
            entry_id=entry_text,
        )
        return (False, None)


@StrategyFactory.register_strategy(AttributeTypes.CROSSREF_DOI)
class CrossrefDOIExtractionStrategy(AttributeExtractionStrategy):
    def __init__(self, warning_manager: WarningManager):
        super().__init__(warning_manager=warning_manager)
        self.log_file_path = LOG_DIR_PATH / "crossref_doi_extraction_strategy.log"
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []
        if not self.logger.handlers:
            handler = logging.FileHandler(self.log_file_path)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            self.logger.addHandler(handler)

    def extract_attribute(self, entry_text: dict) -> tuple[bool, str]:
        doi = entry_text.get("DOI")
        if doi:
            return (True, doi)
        self.log_extraction_warning(
            attribute_class_name=self.__class__.__name__,
            warning_message="Attribute: 'Crossref_DOI' was not found in the entry",
            entry_id=entry_text,
        )
        return (False, None)


@StrategyFactory.register_strategy(AttributeTypes.CROSSREF_THEMES)
class CrossrefThemesExtractionStrategy(AttributeExtractionStrategy):
    def __init__(self, warning_manager: WarningManager):
        super().__init__(warning_manager=warning_manager)
        self.log_file_path = LOG_DIR_PATH / "crossref_themes_extraction_strategy.log"
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []
        if not self.logger.handlers:
            handler = logging.FileHandler(self.log_file_path)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            self.logger.addHandler(handler)

    def extract_attribute(self, entry_text: dict) -> tuple[bool, list[str]]:
        themes = entry_text.get("themes", [])
        return (True, themes)
