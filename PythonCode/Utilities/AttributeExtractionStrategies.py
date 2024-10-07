import re
import warnings
from html import unescape
from bs4 import BeautifulSoup
import json
from abc import ABC, abstractmethod
import uuid

from custom_logging.logger import configure_logger
from strategy_factory import StrategyFactory
from enums import AttributeTypes
from warning_manager import WarningManager


class AttributeExtractionStrategy(ABC):
    def __init__(
        self,
        warning_manager: WarningManager,
        missing_abstracts_file="missing_abstracts.txt",
    ):
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
        raise NotImplementedError("This method must be implemented in a subclass")

    def extract_c1_content(self, entry_text):
        """
        Extracts the 'C1' content from the entry text.

        Parameters:
            entry_text (str): The text of the entry from which to extract the 'C1' content.

        Returns:
            str: The extracted 'C1' content or an empty string if not found.
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
        # Use BeautifulSoup to parse the HTML content
        soup: BeautifulSoup = BeautifulSoup(html_content, "lxml")

        markdown_content: list[str] = []

        # Check if there are any <jats:sec> sections
        sections: list[BeautifulSoup] = soup.find_all("jats:sec")
        if sections:
            for section in sections:
                title = section.find("jats:title")
                if title:
                    string: str = f"## {title.get_text(strip=True)}:"
                    if title.get_text(strip=True).endswith(":"):
                        string = string[:-1]
                    markdown_content.append(string)

                paragraphs: list[BeautifulSoup] = section.find_all("jats:p")
                for paragraph in paragraphs:
                    markdown_content.append(paragraph.get_text(strip=True) + "\n")
        else:
            # If no sections, combine all paragraphs
            paragraphs: list[BeautifulSoup] = soup.find_all("jats:p")
            for paragraph in paragraphs:
                markdown_content.append(paragraph.get_text(strip=True) + "\n")

        return "\n".join(markdown_content)

    def split_salisbury_authors(self, salisbury_authors: str) -> list[str]:
        """
        Splits the authors string at each ';' and stores the items in a list.

        Parameters:
            authors_text (str): The string containing authors separated by ';'.

        Returns:
            list: A list of authors.
        """
        return [
            salisbury_author.strip()
            for salisbury_author in salisbury_authors.split(";")
        ]

    def extract_dept_from_c1(self, entry_text: str) -> list[str]:
        """
        Extracts department and school names from the 'C1' content in the entry text.

        Parameters:
            entry_text (str): The text of the entry from which to extract the content.

        Returns:
            str: Extracted department and school names or an empty string if not found.
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
        raw_affils: list[str] = author_item["affiliation"]
        affils: list[str] = []
        for affil in raw_affils:
            affils.append(affil["name"])
        return affils
    
    def get_author_obj(self, *, crossref_json: dict) -> list[dict]:
        authors: list[dict] = crossref_json.get(self.crossref_author_key, None)
        return authors
    
    def set_author_sequence_dict(
        self, *, author_items: list[dict], author_sequence_dict: dict, unknown_authors_file: str
    ) -> None:
        for author_item in author_items:
            sequence: str = author_item.get("sequence", None)
            author_given_name: str = author_item.get("given", None)
            author_family_name: str = author_item.get("family", None)

            author_name: str = ""
            if author_given_name and author_family_name:
                author_name = f"{author_given_name} {author_family_name}"
            else:
                self.log_extraction_warning(
                    attribute_class_name=self.__class__.__name__,
                    warning_message="Attribute: 'Crossref_Author' was not found in the entry",
                    entry_id=author_item,
                )
                self.unknown_authors["unknown_authors"].append(author_item)
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
                self.unknown_authors["unknown_authors"].append(
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

        self.write_missing_authors_file(self.unknown_authors)
        
    def write_missing_authors_file(self, unknown_authors: dict) -> None:
        with open(self.missing_authors_file, "w") as unknown_authors_file:
            json.dump(unknown_authors, unknown_authors_file, indent=4)
            
    def create_author_sequence_dict(self) -> dict:
        return {"first": {"author_name": "", "affiliations": []}, "additional": []}

    def create_unknown_authors_dict(self) -> dict:
        return {"unknown_authors": []}

    def log_extraction_warning(
        self,
        attribute_class_name: str,
        warning_message: str,
        entry_id: str = None,
        line_prefix: str = None,
    ):
        log_message = f"Failed to extract {attribute_class_name}. Error ID: {self.generate_error_id()}"
        if type(entry_id) == str:
            for line in entry_id.splitlines():
                if line.startswith(line_prefix):
                    log_message += f" - Line: {line}"
        else:
            log_message += f" - Entry ID: {entry_id[:25]}"
        log_message += f" - {warning_message}"
        self.logger.warning(log_message)
        self.warning_manager.log_warning(attribute_class_name, log_message, entry_id)

    def generate_error_id(self) -> str:
        return str(uuid.uuid4())
    
    def write_missing_authors_file(self, unknown_authors: dict, unknown_authors_file: str) -> None:
        with open(unknown_authors_file, "w") as unknown_authors_file:
            json.dump(unknown_authors, unknown_authors_file, indent=4)

    def create_author_sequence_dict(self) -> dict:
        return {"first": {"author_name": "", "affiliations": []}, "additional": []}

    def create_unknown_authors_dict(self) -> dict:
        return {"unknown_authors": []}
    
    def get_author_obj(self, *, crossref_json: dict) -> list[dict]:
        authors: list[dict] = crossref_json.get(self.crossref_author_key, None)
        return authors
    
    def set_author_sequence_dict(
        self, *, author_items: list[dict], author_sequence_dict: dict
    ) -> None:
        for author_item in author_items:
            sequence: str = author_item.get("sequence", None)
            author_given_name: str = author_item.get("given", None)
            author_family_name: str = author_item.get("family", None)

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

        self.write_missing_authors_file(self.unknown_authors_dict, self.unknown_authors_file)

    def get_authors_as_list(self, *, author_sequence_dict: dict) -> list[str]:
        authors: list[str] = []
        authors.append(author_sequence_dict["first"]["author_name"])
        for item in author_sequence_dict["additional"]:
            authors.append(item["author_name"])
        return authors

@StrategyFactory.register_strategy(AttributeTypes.AUTHOR)
class AuthorExtractionStrategy(AttributeExtractionStrategy):
    def __init__(self, warning_manager: WarningManager):
        super().__init__(warning_manager=warning_manager)
        self.author_pattern: re.Pattern = re.compile(r"AF\s(.+?)(?=\nTI)", re.DOTALL)

    def extract_attribute(self, entry_text: str) -> tuple[bool, list[str]]:
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
    def __init__(self, warning_manager: WarningManager):
        super().__init__(warning_manager=warning_manager)
        self.wc_pattern: re.Pattern = re.compile(r"WC\s+(.+?)(?=\nWE)", re.DOTALL)

    def extract_attribute(self, entry_text: str) -> tuple[bool, list[str]]:
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
    def __init__(self, warning_manager: WarningManager):
        super().__init__(warning_manager=warning_manager)
        self.title_pattern: re.Pattern = re.compile(r"TI\s(.+?)(?=\nSO)", re.DOTALL)

    def extract_attribute(self, entry_text: str) -> tuple[bool, str]:
        """
        Extracts the title from the entry text, removing newline characters, HTML tags,
        and condensing multiple spaces into a single space.

        Parameters:
            entry_text (str): The text of the entry from which to extract the title.

        Returns:
            tuple: A tuple containing a boolean indicating whether the extraction was successful,
            and the cleaned title or None.
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
    def __init__(self, warning_manager: WarningManager):
        super().__init__(warning_manager=warning_manager)
        self.abstract_pattern: re.Pattern = re.compile(r"AB\s(.+?)(?=\nC1)", re.DOTALL)

    def extract_attribute(self, entry_text: str) -> tuple[bool, str]:
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
    def __init__(self, warning_manager: WarningManager):
        super().__init__(warning_manager=warning_manager)
        self.end_record_pattern = re.compile(r"DA \d{4}-\d{2}-\d{2}\nER\n?", re.DOTALL)

    def extract_attribute(self, entry_text: str) -> tuple[bool, str]:
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
    def __init__(self, warning_manager: WarningManager):
        super().__init__(warning_manager=warning_manager)
        self.title_key: str = "title"

    def clean_title(self, title: str) -> str:
        # Remove HTML tags using BeautifulSoup
        soup: BeautifulSoup = BeautifulSoup(title, "html.parser")
        return soup.get_text()

    def extract_attribute(self, entry_text: dict) -> tuple[bool, list[str]]:
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
    def __init__(self, warning_manager: WarningManager):
        super().__init__(warning_manager=warning_manager)
        self.abstract_key: str = "abstract"

    def clean_abstract(self, abstract: str) -> str:
        return self.html_to_markdown(abstract)

    def extract_attribute(self, entry_text: dict) -> tuple[bool, str]:
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
    def __init__(self, warning_manager: WarningManager):
        super().__init__(warning_manager=warning_manager)
        self.unknown_authors: dict = self.create_unknown_authors_dict()
        self.missing_authors_file: str = "unknown_authors.json"







    # def get_affiliations(self, author_item: dict) -> list[str]:
    #     return [affil["name"] for affil in author_item.get("affiliation", [])]

    def get_author_name(self, author_item: dict) -> str:
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
        author_items: list[dict] = self.get_author_obj(crossref_json=crossref_json)
        author_sequence_dict: dict = self.create_author_sequence_dict()
        self.set_author_sequence_dict(
            author_items=author_items, author_sequence_dict=author_sequence_dict,
        )
        return (
            True,
            self.get_authors_as_list(author_sequence_dict=author_sequence_dict),
        )

@StrategyFactory.register_strategy(AttributeTypes.CROSSREF_DEPARTMENTS)
class CrossrefDepartmentExtractionStrategy(AttributeExtractionStrategy):
    def __init__(self, warning_manager: WarningManager):
        super().__init__(warning_manager=warning_manager)

    def extract_attribute(self, crossref_json: dict) -> tuple[bool, list[str]]:
        author_items: list[dict] = self.get_author_obj(crossref_json=crossref_json)
        sequence_dict: dict = self.create_author_sequence_dict()
        self.set_author_sequence_dict(
            author_items=author_items, author_sequence_dict=sequence_dict,
        )
        
        # keys are authors, values are their affiliation
        department_affiliations: dict[str, str] = {}
        first_author = sequence_dict.get("first", None)
        if first_author:
            print(f"first_author: {first_author['author_name']}")
            print(f"affiliations: {first_author['affiliations']}")
            department_affiliations[first_author["author_name"]] = first_author["affiliations"]
            
        additional_authors = sequence_dict.get("additional", None)
        if additional_authors:
            for author in additional_authors:
                print(f"author: {author['author_name']}")
                print(f"affiliations: {author['affiliations']}")
                department_affiliations[author["author_name"]] = author["affiliations"]
        
        print(f"department_affiliations: {department_affiliations}")
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
    def __init__(self, warning_manager: WarningManager):
        super().__init__(warning_manager=warning_manager)

    def extract_attribute(self, crossref_json: dict) -> tuple[bool, list[str]]:
        categories = crossref_json.get("categories", None)
        return (
            True if categories else False,
            categories
        )
    
@StrategyFactory.register_strategy(AttributeTypes.CROSSREF_CITATION_COUNT)
class CrossrefCitationCountExtractionStrategy(AttributeExtractionStrategy):
    def __init__(self, warning_manager: WarningManager):
        super().__init__(warning_manager=warning_manager)

    def extract_attribute(self, crossref_json: dict) -> tuple[bool, int]:
        citation_count = crossref_json.get("is-referenced-by-count", 0)
        return (
            True,
            citation_count
        )
