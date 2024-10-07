from fuzzywuzzy import fuzz, process
import collections
from typing import Tuple
from PseudoUniqueFaculty import ConstructPseudoUniqueFaculty
from functools import wraps
from collections import defaultdict
import sys
import json
from dataclasses import dataclass, field, asdict
from typing import Set, List


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

    # this holds the file names associated with articles
    # article_set: Set[str] = field(default_factory=set)

    def to_dict(self) -> dict:
        # Utilize asdict utility from dataclasses, then change sets to lists
        data_dict = asdict(self)

        # Exclude 'files' from the dictionary
        if "files" in data_dict:
            del data_dict["files"]

        # Convert sets to lists for JSON serialization
        for key, value in data_dict.items():
            if isinstance(value, Set):
                data_dict[key] = list(value)
        return data_dict

sys.path.append(
    '.'
)

def helper_method(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


class FuzzyMatcher:
    def __init__(self):
        self.category_dict: dict[str, CategoryInfo] = {}
        with open('processed_category_data.json', 'r') as f:
            json_data = json.load(f)
            for category, data in json_data.items():
                self.category_dict[category] = CategoryInfo(
                    url=data.get('url', ''),
                    faculty_count=data.get('faculty_count', 0),
                    department_count=data.get('department_count', 0),
                    article_count=data.get('article_count', 0),
                    faculty=set(data.get('faculty', [])),
                    departments=set(data.get('departments', [])),
                    titles=set(data.get('titles', [])),
                    tc_count=data.get('tc_count', 0),
                    tc_list=data.get('tc_list', []),
                    citation_average=data.get('citation_average', 0)
                )

        self.faculty_name_groups: dict[str, list[str]] = collections.defaultdict(list)
        cpf = ConstructPseudoUniqueFaculty(self.category_dict)
        self.pseudo_unique_faculty_set: set[str] = cpf.get_pseudo_unique_faculty_set()
        self._create_groups(self.faculty_name_groups, self.pseudo_unique_faculty_set)

    @staticmethod
    def _create_groups(
        faculty_name_groups: dict[str, list[str]], pseudo_unique_set: set[str]
    ) -> None:
        for faculty_name in pseudo_unique_set:
            if faculty_name == "":
                continue
            if ", " in faculty_name:
                last_name, remainder = FuzzyMatcher._get_last_name_and_remainder(
                    faculty_name
                )
                first_initial = (
                    FuzzyMatcher._get_first_initial(remainder) if remainder else ""
                )
            else:
                last_name, first_initial = FuzzyMatcher._extract_last_name_and_initial(
                    faculty_name
                )
            group_key = (last_name, first_initial)
            faculty_name_groups[group_key].append(faculty_name)
            
            print(f"\nAdded '{faculty_name}' to group {group_key}")
            print(f"Current group members: {faculty_name_groups[group_key]}")
            
            # Print fuzzy matching stats for this group
            if len(faculty_name_groups[group_key]) > 1:
                print(f"Fuzzy matching stats for group {group_key}:")
                for name1 in faculty_name_groups[group_key][:-1]:
                    for name2 in faculty_name_groups[group_key][faculty_name_groups[group_key].index(name1)+1:]:
                        ratio = fuzz.ratio(name1, name2)
                        partial_ratio = fuzz.partial_ratio(name1, name2)
                        token_sort_ratio = fuzz.token_sort_ratio(name1, name2)
                        token_set_ratio = fuzz.token_set_ratio(name1, name2)
                        print(f"  {name1} <-> {name2}:")
                        print(f"    Ratio: {ratio}")
                        print(f"    Partial Ratio: {partial_ratio}")
                        print(f"    Token Sort Ratio: {token_sort_ratio}")
                        print(f"    Token Set Ratio: {token_set_ratio}")

    def is_name_in_group(self, name: str) -> Tuple[bool, list[str]]:
        if ", " in name:
            last_name, remainder = FuzzyMatcher._get_last_name_and_remainder(name)
            first_initial = (
                FuzzyMatcher._get_frist_initial(remainder) if remainder else ""
            )
        else:
            last_name, first_initial = FuzzyMatcher._extract_last_name_and_initial(name)
        group_key = (last_name, first_initial)

        if group_key in self.name_groups:
            return True, self.name_groups[group_key]
        return False, []

    @staticmethod
    @helper_method
    def _get_last_name_and_remainder(name: str) -> Tuple[str, str]:
        last_name, remainder = name.split(", ", 1)
        return last_name, remainder

    @staticmethod
    @helper_method
    def _get_first_initial(remainder: str) -> str:
        return remainder[0]

    @staticmethod
    @helper_method
    def _extract_last_name_and_initial(faculty_name: str) -> tuple:
        parts = faculty_name.split(" ", 1)
        if len(parts) == 2:
            last_name, remainder = parts
            first_initial = remainder[0] if remainder else ""
        else:
            # Case for when name is just one string, assumes string is the last name
            last_name = faculty_name
            first_initial = ""
        return last_name, first_initial

    def get_fac_name_groups(self):
        return self.faculty_name_groups

if __name__ == "__main__":
    fm = FuzzyMatcher()
    mydict = fm.get_fac_name_groups()

    print("\nFaculty name groups with multiple names and fuzzy matching stats:")
    for key, names in mydict.items():
        if len(names) > 1:
            print(f"\nGroup: {key}")
            print("Names in this group:")
            for name in names:
                print(f"  - {name}")
            
            print("\nFuzzy matching stats within the group:")
            print("(Higher scores indicate greater similarity)")
            for i, name1 in enumerate(names):
                for name2 in names[i+1:]:
                    ratio = fuzz.ratio(name1, name2)
                    partial_ratio = fuzz.partial_ratio(name1, name2)
                    token_sort_ratio = fuzz.token_sort_ratio(name1, name2)
                    token_set_ratio = fuzz.token_set_ratio(name1, name2)
                    print(f"\n  Comparing: {name1} <-> {name2}")
                    print(f"    Ratio: {ratio} (Similarity of the entire strings)")
                    print(f"    Partial Ratio: {partial_ratio} (Similarity of the best partial match)")
                    print(f"    Token Sort Ratio: {token_sort_ratio} (Similarity after sorting the tokens)")
                    print(f"    Token Set Ratio: {token_set_ratio} (Similarity of unique tokens, regardless of order)")
                    
                    # Interpretation of results
                    print("\n  Interpretation:")
                    if ratio > 90:
                        print("    - Very high overall similarity")
                    elif ratio > 80:
                        print("    - High overall similarity")
                    else:
                        print("    - Moderate to low overall similarity")
                    
                    if partial_ratio > 90:
                        print("    - Contains very similar substrings")
                    elif partial_ratio > 80:
                        print("    - Contains similar substrings")
                    
                    if token_sort_ratio > 90:
                        print("    - Very similar when words are sorted")
                    elif token_sort_ratio > 80:
                        print("    - Similar when words are sorted")
                    
                    if token_set_ratio > 90:
                        print("    - Very similar set of words")
                    elif token_set_ratio > 80:
                        print("    - Similar set of words")
            
            print("-" * 50)