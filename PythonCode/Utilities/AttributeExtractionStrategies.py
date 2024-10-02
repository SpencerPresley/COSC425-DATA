import re
import warnings
from html import unescape
from bs4 import BeautifulSoup
import json
from abc import ABC, abstractmethod

from strategy_factory import StrategyFactory
from enums import AttributeTypes

class AttributeExtractionStrategy(ABC):
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
    
    def html_to_dict(self, soup):
        sections = soup.find_all("jats:sec")
        
        result = {}
        if sections:
            for section in sections:
                title_tag = section.find("jats:title")
                title = title_tag.get_text(strip=True) if title_tag else "No Title"
                paragraphs = section.find_all("jats:p")
                text = " ".join(p.get_text(separator=' ', strip=True) for p in paragraphs)
                result[title] = text
        else:
            # Handle case where there are no <jats:sec> tags
            paragraphs = soup.find_all("jats:p")
            text = " ".join(p.get_text(separator=' ', strip=True) for p in paragraphs)

            result["Abstract"] = text
        
        return result

    def html_to_markdown(self, html_content):
        # Use BeautifulSoup to parse the HTML content
        soup = BeautifulSoup(html_content, 'lxml')
        
        markdown_content = []
        
        # Check if there are any <jats:sec> sections
        sections = soup.find_all('jats:sec')
        if sections:
            for section in sections:
                title = section.find('jats:title')
                if title: 
                    string = f"## {title.get_text(strip=True)}:"
                    if title.get_text(strip=True).endswith(":"):
                        string = string[:-1]
                    markdown_content.append(string)
                
                paragraphs = section.find_all('jats:p')
                for paragraph in paragraphs:
                    markdown_content.append(paragraph.get_text(strip=True) + "\n")
        else:
            # If no sections, combine all paragraphs
            paragraphs = soup.find_all('jats:p')
            for paragraph in paragraphs:
                markdown_content.append(paragraph.get_text(strip=True) + "\n")
        
        return "\n".join(markdown_content)

    
    def split_salisbury_authors(self, salisbury_authors):
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

    def extract_dept_from_c1(self, entry_text):
        """
        Extracts department and school names from the 'C1' content in the entry text.

        Parameters:
            entry_text (str): The text of the entry from which to extract the content.

        Returns:
            str: Extracted department and school names or an empty string if not found.
        """
        c1_content = []
        capturing = False
        entry_lines = entry_text.splitlines()
        for line in entry_lines:
            if line.startswith("C1"):
                capturing = True
            elif line.startswith("C3"):
                capturing = False
            if capturing and "Salisbury" in line:
                # Extract department and school names
                dept_match = re.search(self.dept_pattern, line)
                dept_match_alt = re.search(self.dept_pattern_alt, line)
                if dept_match:
                    c1_content.append(dept_match.group(1))
                elif dept_match_alt:
                    c1_content.append(dept_match_alt.group(1))
        # return '\n'.join(c1_content)
        return c1_content

    def get_crossref_author_affils(self, author_item):
        raw_affils = author_item["affiliation"]
        affils: list[str] = []
        for affil in raw_affils:
            affils.append(affil["name"])
        return affils

@StrategyFactory.register_strategy(AttributeTypes.AUTHOR)
class AuthorExtractionStrategy(AttributeExtractionStrategy):
    def __init__(self):
        self.author_pattern = re.compile(r"AF\s(.+?)(?=\nTI)", re.DOTALL)

    def extract_attribute(self, entry_text):
        author_c1_content = self.extract_c1_content(entry_text)

        # Use the get_salisbury_authors method to extract authors affiliated with Salisbury University
        salisbury_authors = self.split_salisbury_authors(author_c1_content)

        result = ()

        if salisbury_authors:
            result = (True, salisbury_authors)
        else:
            result = (False, None)
            warnings.warn(
                "Attribute: 'Author' was not found in the entry", RuntimeWarning
            )

        return result

@StrategyFactory.register_strategy(AttributeTypes.DEPARTMENT)
class DepartmentExtractionStrategy(AttributeExtractionStrategy):
    def __init__(self):
        self.dept_pattern = re.compile(r"Dept (.*?)(,|$)")
        self.dept_pattern_alt = re.compile(r"Dept, (.*?) ,")

    def extract_attribute(self, entry_text):
        departments = self.extract_dept_from_c1(entry_text)
        return (True, departments) if departments else (False, None)

@StrategyFactory.register_strategy(AttributeTypes.WC_PATTERN)
class WosCategoryExtractionStrategy(AttributeExtractionStrategy):
    def __init__(self):
        self.wc_pattern = re.compile(r"WC\s+(.+?)(?=\nWE)", re.DOTALL)

    def extract_attribute(self, entry_text):
        match = self.wc_pattern.search(entry_text)
        if match:
            categories = self.wos_category_splitter(match.group(1).strip())
            for i, category in enumerate(categories):
                category = re.sub(r"\s+", " ", category)
                categories[i] = category
            return True, categories
        warnings.warn(
            f"Attribute: 'WoS_Category' was not found in the entry", RuntimeWarning
        )
        return False, None

    def wos_category_splitter(self, category_string):
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
    def __init__(self):
        self.title_pattern = re.compile(r"TI\s(.+?)(?=\nSO)", re.DOTALL)

    def extract_attribute(self, entry_text):
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
            title = match.group(1).strip()
            # Remove newline characters
            title = title.replace("\n", " ")
            # Remove HTML tags
            title = re.sub(r"<[^>]+>", "", title)
            # Unescape HTML entities
            title = unescape(title)
            # Condense multiple spaces into a single space
            title = re.sub(r"\s+", " ", title)
            return True, title
        else:
            warnings.warn(
                "Attribute: 'Title' was not found in the entry", RuntimeWarning
            )
            return False, None
    
@StrategyFactory.register_strategy(AttributeTypes.ABSTRACT)
class AbstractExtractionStrategy(AttributeExtractionStrategy):
    def __init__(self):
        self.abstract_pattern = re.compile(r"AB\s(.+?)(?=\nC1)", re.DOTALL)
        self.missing_abstracts_file = "missing_abstracts.txt"
    
    def extract_attribute(self, entry_text):
        match = self.abstract_pattern.search(entry_text)
        if not match:
            with open(self.missing_abstracts_file, "a") as file:
                file.write(f"Missing 'Abstract' in entry:\n{entry_text}\n\n")
            print(
                f"An entry missing 'Abstract' has been written to {self.missing_abstracts_file}."
            )
            warnings.warn(
                "Attribute: 'Abstract' was not found in the entry", RuntimeWarning
            )
            return False, None
        return True, match.group(1).strip()

@StrategyFactory.register_strategy(AttributeTypes.END_RECORD)
def EndRecordExtractionStrategy(AttributeExtractionStrategy):
    def __init__(self):
        self.end_record_pattern = re.compile(r"DA \d{4}-\d{2}-\d{2}\nER\n?", re.DOTALL)
        
    def extract_attribute(self, entry_text):
        match = self.end_record_pattern.search(entry_text)
        if not match:
            warnings.warn(
                "Attribute: 'End_Record' was not found in the entry", RuntimeWarning
            )
            return False, None
        return True, match.group(0).strip()

@StrategyFactory.register_strategy(AttributeTypes.CROSSREF_TITLE)
class CrossrefTitleExtractionStrategy(AttributeExtractionStrategy):
    def __init__(self):
        self.title_key = "title"
        
    def clean_title(self, title):
        # Remove HTML tags using BeautifulSoup
        soup = BeautifulSoup(title, 'html.parser')
        return soup.get_text()
    
    def extract_attribute(self, entry_text):
        titles = entry_text.get(self.title_key, [])
        if not isinstance(titles, list):
            titles = [titles]
        cleaned_titles = [self.clean_title(title) for title in titles]
        return (True, cleaned_titles) if cleaned_titles else (False, None)
        
@StrategyFactory.register_strategy(AttributeTypes.CROSSREF_ABSTRACT)
class CrossrefAbstractExtractionStrategy(AttributeExtractionStrategy):
    def __init__(self):
        self.abstract_key = "abstract"
        
    def clean_abstract(self, abstract):
        return self.html_to_markdown(abstract)
    
    def extract_attribute(self, entry_text):
        abstract = entry_text.get(self.abstract_key, None)
        if abstract:
            abstract = self.clean_abstract(abstract)
            return (True, abstract)
        warnings.warn(
            f"Attribute: 'Crossref_Abstract' was not found in the entry", RuntimeWarning
        )
        return (False, None)
        
@StrategyFactory.register_strategy(AttributeTypes.CROSSREF_AUTHORS)
class CrossrefAuthorExtractionStrategy(AttributeExtractionStrategy):
    def __init__(self):
        self.author_key = "author"
        self.unknown_authors = self.create_unknown_authors_dict()

    def create_author_sequence_dict(self):
        return {
            "first": {
                "author_name": "",
                "affiliations": []
            },
            "additional": []
        }

    def create_unknown_authors_dict(self):
        return {
            "unknown_authors": []
        }

    def write_missing_authors_file(self, unknown_authors:dict[str, list[str]]):
        with open('unknown_authors.json', 'w') as unknown_authors_file:
            json.dump(unknown_authors, unknown_authors_file, indent=4)

    def get_author_obj(self, *, crossref_json):
        authors = crossref_json.get("author", None)
        return authors
    
    def set_author_sequence_dict(self, *, author_items, author_sequence_dict):
        for author_item in author_items:
            sequence = author_item.get("sequence", None)
            author_given_name = author_item.get("given", None)
            author_family_name = author_item.get("family", None)

            author_name = ""
            if author_given_name and author_family_name:
                author_name = f"{author_given_name} {author_family_name}"
            else:
                warnings.warn("Author name not found, being added to unknown authors file", RuntimeWarning)
                self.unknown_authors["unknown_authors"].append(author_item)
                continue

            author_affiliations = self.get_crossref_author_affils(author_item)

            if sequence == "first":
                author_sequence_dict[sequence]["author_name"] = author_name
                for affiliation in author_affiliations:
                    author_sequence_dict[sequence]["affiliations"].append(affiliation)

            elif sequence == "additional":
                additional_author_dict = {}
                additional_author_dict["author_name"] = author_name
                additional_author_dict["affiliations"] = []
                for affiliation in author_affiliations:
                    additional_author_dict["affiliations"].append(affiliation)
                author_sequence_dict["additional"].append(additional_author_dict)

        self.write_missing_authors_file(self.unknown_authors)
    
    def get_authors_as_list(self, *, author_sequence_dict):
        authors = []
        authors.append(author_sequence_dict["first"]["author_name"])
        for item in author_sequence_dict["additional"]:
            authors.append(item["author_name"])
        return authors
    

    def extract_attribute(self, crossref_json):
        author_items = self.get_author_obj(crossref_json=crossref_json)
        author_sequence_dict = self.create_author_sequence_dict()
        self.set_author_sequence_dict(author_items=author_items, author_sequence_dict=author_sequence_dict)
        return (True, self.get_authors_as_list(author_sequence_dict=author_sequence_dict))
