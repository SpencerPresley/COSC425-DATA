import json
import re
import sys
from typing import Dict, Set, List
from dataclasses import dataclass, field, asdict


@dataclass
class CategoryInfo:
    url: str = ""
    faculty_count: int = 0
    department_count: int = 0
    article_count: int = 0
    files: Set[str] = field(default_factory=set)
    faculty: Set[str] = field(default_factory=set)
    departments: Set[str] = field(default_factory=set)
    titles: Set[str] = field(default_factory=set)
    tc_count: int = 0
    tc_list: List[int] = field(default_factory=list)
    citation_average: int = 0

    def to_dict(self) -> dict:
        data_dict = asdict(self)
        if "files" in data_dict:
            del data_dict["files"]
        for key, value in data_dict.items():
            if isinstance(value, Set):
                data_dict[key] = list(value)
        return data_dict


class TitleExtractor:
    def __init__(
        self,
        json_file_path,
        primary_pattern,
        secondary_pattern,
        output_file_name,
        primary_group=1,
        secondary_group=1,
    ):
        self.json_file_path = json_file_path
        self.primary_pattern = primary_pattern
        self.secondary_pattern = secondary_pattern
        self.output_file_name = output_file_name
        self.primary_group = primary_group
        self.secondary_group = secondary_group
        self.citation_count = 0
        self.match_count = 0
        self.non_match_count = 0
        self.non_match_titles = []
        self.titles = []
        self.data = self.load_json_data()
        self.output_file = open(self.output_file_name, "w")
        self.original_stdout = sys.stdout
        sys.stdout = self

    def __del__(self):
        self.output_file.close()
        sys.stdout = self.original_stdout

    def write(self, message):
        self.output_file.write(message)
        self.output_file.flush()

    def flush(self):
        self.output_file.flush()

    def load_json_data(self):
        with open(self.json_file_path, "r") as file:
            return json.load(file)

    def extract_titles(self):
        category_name = list(self.data.keys())[0]  # Get the first (and only) key
        for item in self.data[category_name]:
            if "Citation" in item:
                self.citation_count += 1
                citation = item["Citation"]

                match = re.match(self.primary_pattern, citation)
                if match:
                    self.match_count += 1
                    title = match.group(self.primary_group).strip()
                    self.titles.append(title)
                else:
                    self.non_match_count += 1
                    self.non_match_titles.append(citation)
        return self.titles

    def process_non_matching_titles(self):
        additional_titles = []
        processed_citations = []
        for citation in self.non_match_titles:
            match = re.search(self.secondary_pattern, citation)
            if match:
                title = match.group(self.secondary_group).strip()
                additional_titles.append(title)
                processed_citations.append(citation)
                self.match_count += 1
                self.non_match_count -= 1
        self.titles.extend(additional_titles)
        self.non_match_titles = [
            citation
            for citation in self.non_match_titles
            if citation not in processed_citations
        ]

    def get_titles(self):
        self.extract_titles()
        self.process_non_matching_titles()
        return self.titles

    def print_stats(self):
        # print("Starting program...")
        # print("CategoryInfo class defined...")

        def dict_to_category_info(data: Dict) -> CategoryInfo:
            return CategoryInfo(
                url=data.get("url", ""),
                faculty_count=data.get("faculty_count", 0),
                department_count=data.get("department_count", 0),
                article_count=data.get("article_count", 0),
                faculty=set(data.get("faculty", [])),
                departments=set(data.get("departments", [])),
                titles=set(data.get("titles", [])),
                tc_count=data.get("tc_count", 0),
                tc_list=data.get("tc_list", []),
                citation_average=data.get("citation_average", 0),
            )

        def get_all_titles(categories: Dict[str, CategoryInfo]) -> Set[str]:
            all_titles = set()
            for category in categories.values():
                all_titles.update(category.titles)
            return all_titles

        # print("Converting data to CategoryInfo objects...")
        with open("PythonCode/Utilities/test_processed_category_data.json", "r") as file:
            data = json.load(file)
        categories = {name: dict_to_category_info(info) for name, info in data.items()}

        # print("Getting all titles from processed category data...")
        titles_from_processed_category_data = get_all_titles(categories)

        # print("Printing all titles from processed category data...")
        # for title in titles_from_processed_category_data:
        #     print(title)

        titles_set = set()
        processed_titles_set = set()

        title_tracker = {}
        processed_title_tracker = {}
        print("Printing all titles from extracted titles...")
        for title in self.titles:
            print(title)
            normalized_title = title.lower()
            normalized_title = re.sub(r"\s+", "", normalized_title).strip()

            if normalized_title not in title_tracker:
                title_tracker[normalized_title] = title
                titles_set.add(normalized_title)

        for title in titles_from_processed_category_data:
            normalized_title = title.lower()
            normalized_title = re.sub(r"\s+", "", normalized_title).strip()

            if normalized_title not in processed_title_tracker:
                processed_title_tracker[normalized_title] = title
                processed_titles_set.add(normalized_title)

        first_verification_set = titles_set - processed_titles_set

        print("\nTitles in extracted titles but not in processed category data...")
        for i, title in enumerate(first_verification_set, 1):
            print(f"{i}. {title_tracker[title]}")


# Usage
accounting_primary_pattern = r"\.\s*\(\d{4}\)\.\s*([^\.]+)\."
accounting_secondary_pattern = (
    r"(?:(?:[A-Z][a-z]+,\s[A-Z]\.(?:\s[A-Z]\.)?,?\s)+)([^\.]+)\."
)

accounting_extractor = TitleExtractor(
    "assets/json_data/Accounting-and-Legal-Studies.json",
    accounting_primary_pattern,
    accounting_secondary_pattern,
    "accounting_output.txt",
    primary_group=2,
    secondary_group=1,
)
accounting_titles = accounting_extractor.get_titles()
accounting_extractor.print_stats()

# You can define different patterns for Economics if needed
economics_primary_pattern = r"^[^\.]+\.\s*\(\d{4}\)\.\s*([^\.]+)\."
economics_secondary_pattern = (
    r"(?:(?:[A-Z][a-z]+,\s[A-Z]\.(?:\s[A-Z]\.)?,?\s)+)([^\.]+)\."
)


economics_extractor = TitleExtractor(
    "assets/json_data/Economics.json",
    economics_primary_pattern,
    economics_secondary_pattern,
    "economics_output.txt",
    primary_group=1,
    secondary_group=1,
)
economics_titles = economics_extractor.get_titles()
economics_extractor.print_stats()
