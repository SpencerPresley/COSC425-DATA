import re
import warnings
from html import unescape
from bs4 import BeautifulSoup
import json
from abc import ABC, abstractmethod
import uuid

from academic_metrics.utils import configure_logger, WarningManager
from .strategy_factory import StrategyFactory
from academic_metrics.enums import AttributeTypes


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
        extract_c1_content: Extracts content from the 'C1' field of publication data.
        html_to_dict: Converts HTML content to a structured dictionary.
        html_to_markdown: Converts HTML content to Markdown format.
        split_salisbury_authors: Splits a string of Salisbury University authors into a list.
        extract_dept_from_c1: Extracts department information from the 'C1' field.
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
        self.logger = configure_logger(
            name=self.__class__.__name__,
            log_file_name="attribute_extraction_strategies.log",
        )
        self.abstract_pattern = re.compile(r"AB\s(.+?)(?=\nC1)", re.DOTALL)
        self.missing_abstracts_file = missing_abstracts_file
        self.warning_manager = warning_manager
        self.unknown_authors_dict = self.create_unknown_authors_dict()
        self.unknown_authors_file = "crossref_unknown_authors.json"
        self.crossref_author_key: str = "author"

    @abstractmethod
    def extract_attribute(self, entry_text):
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

    def extract_c1_content(self, entry_text):
        """
        Extracts the 'C1' content from the entry text.

        This method searches for lines containing "Salisbury Univ" and extracts
        the content within square brackets from those lines.

        Args:
            entry_text (str): The text of the entry from which to extract the 'C1' content.

        Returns:
            str: The extracted 'C1' content or an empty string if not found.

        Design:
            Uses string manipulation to find and extract relevant content.

        Summary:
            Extracts institution-specific content from the entry text.

        This is used by various subclasses who are designed to extract attributes from WoS data, this is NOT compatible with Crossref data.
        """
        c1_content = []
        entry_lines = entry_text.splitlines()
        for line in entry_lines:
            if "Salisbury Univ" in line:
                # Extract everything inside the brackets
                start = line.find("[")
                end = line.find("]")
                if start != -1 and end != -1:
                    c1_content.append(line[start + 1 : end])
                break
        return "\n".join(c1_content)

    def html_to_dict(self, soup: BeautifulSoup) -> dict:
        """
        Converts HTML content to a structured dictionary.

        This method parses HTML content, specifically looking for JATS XML tags,
        and organizes the content into a dictionary format.

        It is aimed to be used with Crossref data, not WoS data. It is intented to clean the abstract field of Crossref data from having JATS XML tags, then recombines the abstract into a single string and inserts it into the dictionary under the key "Abstract".

        Args:
            soup (BeautifulSoup): A BeautifulSoup object containing the parsed HTML.

        Returns:
            dict: A dictionary where keys are section titles and values are the corresponding text content.

        Design:
            Uses BeautifulSoup to parse and extract content from specific XML tags.
            Handles cases with and without section tags.

        Summary:
            Transforms HTML content into a structured dictionary format for easier processing.
        """
        sections: list[BeautifulSoup] = soup.find_all("jats:sec")

        result: dict = {}
        if sections:
            for section in sections:
                title_tag: BeautifulSoup = section.find("jats:title")
                title: str = title_tag.get_text(strip=True) if title_tag else "No Title"
                paragraphs: list[BeautifulSoup] = section.find_all("jats:p")
                text: str = " ".join(
                    p.get_text(separator=" ", strip=True) for p in paragraphs
                )
                result[title] = text
        else:
            # Handle case where there are no <jats:sec> tags
            paragraphs: list[BeautifulSoup] = soup.find_all("jats:p")
            text: str = " ".join(
                p.get_text(separator=" ", strip=True) for p in paragraphs
            )

            result["Abstract"] = text

        return result

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

    def split_salisbury_authors(self, salisbury_authors: str) -> list[str]:
        """
        Splits a string of Salisbury University authors into a list.

        This method takes a string of authors separated by semicolons and
        returns a list of individual author names.

        This is implemented in the base class as it used by more than a single subclass. It is designed to be used with WoS data, not Crossref data. It is NOT compatible with Crossref data.

        Args:
            salisbury_authors (str): A string of authors separated by semicolons.

        Returns:
            list[str]: A list of individual author names.

        Design:
            Uses string splitting and list comprehension for efficient processing.

        Summary:
            Converts a semicolon-separated string of authors into a list of names.
        """
        return [
            salisbury_author.strip()
            for salisbury_author in salisbury_authors.split(";")
        ]

    def extract_dept_from_c1(self, entry_text: str) -> list[str]:
        """
        Extracts department names from the 'C1' content in the entry text.

        This method searches for department information within the 'C1' field
        of the entry text, specifically looking for Salisbury University affiliations.

        It is designed to be used with WoS data, not Crossref data. It is NOT compatible with Crossref data.

        Args:
            entry_text (str): The full text of the entry containing 'C1' content.

        Returns:
            list[str]: A list of extracted department names.

        Design:
            Uses regular expressions to match department patterns in the text.
            Handles multiple possible department name formats.

        Summary:
            Extracts and returns a list of department names from the entry text.
        """
        c1_content: list[str] = []
        capturing: bool = False
        entry_lines: list[str] = entry_text.splitlines()
        for line in entry_lines:
            if line.startswith("C1"):
                capturing = True
            elif line.startswith("C3"):
                capturing = False
            if capturing and "Salisbury" in line:
                # Extract department and school names
                dept_match: re.Match = re.search(self.dept_pattern, line)
                dept_match_alt: re.Match = re.search(self.dept_pattern_alt, line)
                if dept_match:
                    c1_content.append(dept_match.group(1))
                elif dept_match_alt:
                    c1_content.append(dept_match_alt.group(1))
        return c1_content

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


@StrategyFactory.register_strategy(AttributeTypes.AUTHOR)
class AuthorExtractionStrategy(AttributeExtractionStrategy):
    """
    A strategy for extracting author information from Web of Science (WoS) data.

    This class implements the AttributeExtractionStrategy for author extraction
    specifically from WoS entry text. It focuses on identifying authors affiliated
    with Salisbury University.

    Attributes:
        author_pattern (re.Pattern): A compiled regular expression for matching author information.

    Methods:
        extract_attribute: Extracts Salisbury University affiliated authors from the entry text.

    Design:
        Utilizes regular expressions and inherited methods to parse and extract author information.
        Implements the Strategy pattern for author extraction from WoS data.

    Summary:
        Provides a specialized strategy for extracting Salisbury University affiliated authors
        from Web of Science publication data.
    """

    def __init__(self, warning_manager: WarningManager):
        """
        Initializes the AuthorExtractionStrategy.

        This constructor sets up the strategy with a warning manager and compiles
        the regular expression pattern for author extraction.

        Args:
            warning_manager (WarningManager): An instance of WarningManager for handling extraction warnings.

        Returns:
            None

        Design:
            Calls the superclass constructor and compiles a specific regular expression for author matching.

        Summary:
            Prepares the strategy instance for author extraction from WoS data.
        """
        super().__init__(warning_manager=warning_manager)
        self.author_pattern: re.Pattern = re.compile(r"AF\s(.+?)(?=\nTI)", re.DOTALL)

    def extract_attribute(self, entry_text: str) -> tuple[bool, list[str]]:
        """
        Extracts Salisbury University affiliated authors from the entry text.

        This method parses the entry text to find authors affiliated with Salisbury University.
        It is designed to work with Web of Science (WoS) data format.

        Args:
            entry_text (str): The full text of the WoS entry.

        Returns:
            tuple[bool, list[str]]: A tuple containing:
                - A boolean indicating success (True) or failure (False) of the extraction.
                - A list of extracted Salisbury University affiliated author names, or None if no authors found.

        Design:
            Uses the extract_c1_content and split_salisbury_authors methods to process the entry text.
            Logs a warning if no Salisbury authors are found.

        Summary:
            Extracts and returns a list of Salisbury University affiliated authors from WoS entry text.
        """
        author_c1_content: str = self.extract_c1_content(entry_text)

        # Use the get_salisbury_authors method to extract authors affiliated with Salisbury University
        salisbury_authors: list[str] = self.split_salisbury_authors(author_c1_content)

        result: tuple[bool, list[str]] = ()

        if salisbury_authors:
            return (True, salisbury_authors)
        else:
            self.log_extraction_warning(
                attribute_class_name=self.__class__.__name__,
                warning_message="No Salisbury authors found in the entry",
                entry_id=entry_text,
                line_prefix="AF",
            )
            return (False, None)


@StrategyFactory.register_strategy(AttributeTypes.DEPARTMENT)
class DepartmentExtractionStrategy(AttributeExtractionStrategy):
    def __init__(self, warning_manager: WarningManager):
        super().__init__(warning_manager=warning_manager)
        self.dept_pattern: re.Pattern = re.compile(r"Dept (.*?)(,|$)")
        self.dept_pattern_alt: re.Pattern = re.compile(r"Dept, (.*?) ,")

    def extract_attribute(self, entry_text: str) -> tuple[bool, list[str]]:
        departments: list[str] = self.extract_dept_from_c1(entry_text)
        if departments:
            return (True, departments)
        else:
            self.log_extraction_warning(
                attribute_class_name=self.__class__.__name__,
                warning_message="Attribute: 'Department' was not found in the entry",
                entry_id=entry_text,
                line_prefix="C1",
            )
            return (False, None)


@StrategyFactory.register_strategy(AttributeTypes.WC_PATTERN)
class WosCategoryExtractionStrategy(AttributeExtractionStrategy):
    """
    A strategy for extracting department information from Web of Science (WoS) data.

    This class implements the AttributeExtractionStrategy for department extraction
    specifically from WoS entry text. It focuses on identifying department names
    associated with Salisbury University affiliations.

    Attributes:
        dept_pattern (re.Pattern): A compiled regular expression for matching department names.
        dept_pattern_alt (re.Pattern): An alternative compiled regular expression for department names.

    Methods:
        extract_attribute: Extracts department names from the entry text.

    Design:
        Utilizes regular expressions and inherited methods to parse and extract department information.
        Implements the Strategy pattern for department extraction from WoS data.

    Summary:
        Provides a specialized strategy for extracting department names
        from Web of Science publication data, focusing on Salisbury University affiliations.
    """

    def __init__(self, warning_manager: WarningManager):
        """
        Initializes the DepartmentExtractionStrategy.

        This constructor sets up the strategy with a warning manager and compiles
        the regular expression patterns for department extraction.

        Args:
            warning_manager (WarningManager): An instance of WarningManager for handling extraction warnings.

        Returns:
            None

        Design:
            Calls the superclass constructor and compiles specific regular expressions for department matching.

        Summary:
            Prepares the strategy instance for department extraction from WoS data.
        """
        super().__init__(warning_manager=warning_manager)
        self.wc_pattern: re.Pattern = re.compile(r"WC\s+(.+?)(?=\nWE)", re.DOTALL)

    def extract_attribute(self, entry_text: str) -> tuple[bool, list[str]]:
        """
        Extracts department names from the entry text.

        This method parses the entry text to find department names associated with Salisbury University.
        It is designed to work with Web of Science (WoS) data format.

        Args:
            entry_text (str): The full text of the WoS entry.

        Returns:
            tuple[bool, list[str]]: A tuple containing:
                - A boolean indicating success (True) or failure (False) of the extraction.
                - A list of extracted department names, or None if no departments found.

        Design:
            Uses the extract_dept_from_c1 method to process the entry text.
            Logs a warning if no departments are found.

        Summary:
            Extracts and returns a list of department names from WoS entry text.
        """
        match = self.wc_pattern.search(entry_text)
        if match:
            categories: list[str] = self.wos_category_splitter(match.group(1).strip())
            for i, category in enumerate(categories):
                category: str = re.sub(r"\s+", " ", category)
                categories[i] = category
            return (True, categories)
        else:
            self.log_extraction_warning(
                attribute_class_name=self.__class__.__name__,
                warning_message="Attribute: 'WoS_Category' was not found in the entry",
                entry_id=entry_text,
                line_prefix="WC",
            )
            return (False, None)

    def wos_category_splitter(self, category_string: str) -> list[str]:
        """
        Splits a string of Web of Science (WoS) categories into a list of individual categories.

        This method is specifically designed to process strings where categories are separated by semicolons (';').
        It strips any leading or trailing whitespace from each category after splitting.

        Parameters:
            category_string (str): The string containing the categories, with each category separated by a semicolon (';').

        Returns:
            list: A list of strings, where each string is a trimmed category extracted from the input string.
        """
        return [category.strip() for category in category_string.split(";")]


@StrategyFactory.register_strategy(AttributeTypes.TITLE)
class TitleExtractionStrategy(AttributeExtractionStrategy):
    """
    A strategy for extracting title information from Web of Science (WoS) data.

    This class implements the AttributeExtractionStrategy for title extraction
    specifically from WoS entry text. It focuses on extracting and cleaning
    the title of a publication.

    Attributes:
        title_pattern (re.Pattern): A compiled regular expression for matching title information.

    Methods:
        extract_attribute: Extracts and cleans the title from the entry text.

    Design:
        Utilizes regular expressions and string manipulation to extract and clean the title.
        Implements the Strategy pattern for title extraction from WoS data.

    Summary:
        Provides a specialized strategy for extracting and cleaning publication titles
        from Web of Science data entries.
    """

    def __init__(self, warning_manager: WarningManager):
        """
        Initializes the TitleExtractionStrategy.

        This constructor sets up the strategy with a warning manager and compiles
        the regular expression pattern for title extraction.

        Args:
            warning_manager (WarningManager): An instance of WarningManager for handling extraction warnings.

        Returns:
            None

        Design:
            Calls the superclass constructor and compiles a specific regular expression for title matching.

        Summary:
            Prepares the strategy instance for title extraction from WoS data.
        """
        super().__init__(warning_manager=warning_manager)
        self.title_pattern: re.Pattern = re.compile(r"TI\s(.+?)(?=\nSO)", re.DOTALL)

    def extract_attribute(self, entry_text: str) -> tuple[bool, str]:
        """
        Extracts and cleans the title from the entry text.

        This method parses the entry text to find the title, then cleans it by removing
        newline characters, HTML tags, and condensing multiple spaces. It is designed
        to work with Web of Science (WoS) data format.

        Args:
            entry_text (str): The full text of the WoS entry.

        Returns:
            tuple[bool, str]: A tuple containing:
                - A boolean indicating success (True) or failure (False) of the extraction.
                - The cleaned title string, or None if no title was found.

        Design:
            Uses regular expressions to extract the title and clean it.
            Handles HTML entities and formatting issues in the title.
            Logs a warning if no title is found.

        Summary:
            Extracts, cleans, and returns the publication title from WoS entry text.
        """
        match = self.title_pattern.search(entry_text)
        if match:
            title: str = match.group(1).strip()
            # Remove newline characters
            title = title.replace("\n", " ")
            # Remove HTML tags
            title = re.sub(r"<[^>]+>", "", title)
            # Unescape HTML entities
            title = unescape(title)
            # Condense multiple spaces into a single space
            title = re.sub(r"\s+", " ", title)
            return (True, title)
        else:
            self.log_extraction_warning(
                attribute_class_name=self.__class__.__name__,
                warning_message="Attribute: 'Title' was not found in the entry",
                entry_id=entry_text,
                line_prefix="TI",
            )
            return (False, None)


@StrategyFactory.register_strategy(AttributeTypes.ABSTRACT)
class AbstractExtractionStrategy(AttributeExtractionStrategy):
    """
    A strategy for extracting abstract information from Web of Science (WoS) data.

    This class implements the AttributeExtractionStrategy for abstract extraction
    specifically from WoS entry text. It focuses on extracting the abstract
    of a publication.

    Attributes:
        abstract_pattern (re.Pattern): A compiled regular expression for matching abstract information.

    Methods:
        extract_attribute: Extracts the abstract from the entry text.

    Design:
        Utilizes regular expressions to extract the abstract content.
        Implements the Strategy pattern for abstract extraction from WoS data.

    Summary:
        Provides a specialized strategy for extracting publication abstracts
        from Web of Science data entries.
    """

    def __init__(self, warning_manager: WarningManager):
        """
        Initializes the AbstractExtractionStrategy.

        This constructor sets up the strategy with a warning manager and compiles
        the regular expression pattern for abstract extraction.

        Args:
            warning_manager (WarningManager): An instance of WarningManager for handling extraction warnings.

        Returns:
            None

        Design:
            Calls the superclass constructor and compiles a specific regular expression for abstract matching.

        Summary:
            Prepares the strategy instance for abstract extraction from WoS data.
        """
        super().__init__(warning_manager=warning_manager)
        self.abstract_pattern: re.Pattern = re.compile(r"AB\s(.+?)(?=\nC1)", re.DOTALL)

    def extract_attribute(self, entry_text: str) -> tuple[bool, str]:
        """
        Extracts the abstract from the entry text.

        This method parses the entry text to find the abstract. It is designed
        to work with Web of Science (WoS) data format.

        Args:
            entry_text (str): The full text of the WoS entry.

        Returns:
            tuple[bool, str]: A tuple containing:
                - A boolean indicating success (True) or failure (False) of the extraction.
                - The extracted abstract string, or None if no abstract was found.

        Design:
            Uses regular expressions to extract the abstract.
            Logs a warning if no abstract is found.

        Summary:
            Extracts and returns the publication abstract from WoS entry text.
        """
        match = self.abstract_pattern.search(entry_text)
        if not match:
            self.log_extraction_warning(
                attribute_class_name=self.__class__.__name__,
                warning_message="Attribute: 'Abstract' was not found in the entry",
                entry_id=entry_text,
                line_prefix="AB",
            )
            return (False, None)
        return (True, match.group(1).strip())


@StrategyFactory.register_strategy(AttributeTypes.END_RECORD)
class EndRecordExtractionStrategy(AttributeExtractionStrategy):
    """
    A strategy for extracting the end record marker from Web of Science (WoS) data.

    This class implements the AttributeExtractionStrategy for end record extraction
    specifically from WoS entry text. It focuses on identifying the end of a record
    in the WoS data format.

    Attributes:
        end_record_pattern (re.Pattern): A compiled regular expression for matching the end record marker.

    Methods:
        extract_attribute: Extracts the end record marker from the entry text.

    Design:
        Utilizes regular expressions to identify the end record marker.
        Implements the Strategy pattern for end record extraction from WoS data.

    Summary:
        Provides a specialized strategy for extracting the end record marker
        from Web of Science data entries, which is crucial for parsing multi-record files.
    """

    def __init__(self, warning_manager: WarningManager):
        """
        Initializes the EndRecordExtractionStrategy.

        This constructor sets up the strategy with a warning manager and compiles
        the regular expression pattern for end record extraction.

        Args:
            warning_manager (WarningManager): An instance of WarningManager for handling extraction warnings.

        Returns:
            None

        Design:
            Calls the superclass constructor and compiles a specific regular expression for end record matching.

        Summary:
            Prepares the strategy instance for end record extraction from WoS data.
        """
        super().__init__(warning_manager=warning_manager)
        self.end_record_pattern = re.compile(r"DA \d{4}-\d{2}-\d{2}\nER\n?", re.DOTALL)

    def extract_attribute(self, entry_text: str) -> tuple[bool, str]:
        """
        Extracts the end record marker from the entry text.

        This method parses the entry text to find the end record marker. It is designed
        to work with Web of Science (WoS) data format, looking for a specific pattern
        that indicates the end of a record.

        Args:
            entry_text (str): The full text of the WoS entry.

        Returns:
            tuple[bool, str]: A tuple containing:
                - A boolean indicating success (True) or failure (False) of the extraction.
                - The extracted end record marker string, or None if not found.

        Design:
            Uses regular expressions to extract the end record marker.
            Logs a warning if the end record marker is not found.

        Summary:
            Extracts and returns the end record marker from WoS entry text, which is crucial
            for determining the boundaries of individual records in multi-record files.
        """
        match = self.end_record_pattern.search(entry_text)
        if not match:
            self.log_extraction_warning(
                attribute_class_name=self.__class__.__name__,
                warning_message="End Record was not found in the entry",
                entry_id=entry_text,
                line_prefix="ER",
            )
            return (False, None)
        return (True, match.group(0).strip())


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
    def extract_attribute(self, entry_text: dict) -> tuple[bool, list[str]]:
        themes = entry_text.get("categories", {}).get("themes", [])
        return (True, themes)
