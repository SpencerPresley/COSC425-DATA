import json
import re
import string
from typing import Dict, Set, List
from dataclasses import dataclass, field, asdict
from difflib import SequenceMatcher

print("Starting program...")

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

print("CategoryInfo class defined...")

def dict_to_category_info(data: Dict) -> CategoryInfo:
    return CategoryInfo(
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

print("dict_to_category_info function defined...")

def normalize_title(title: str) -> str:
    # Convert to lowercase, strip leading/trailing whitespace, replace multiple spaces with a single space, and remove punctuation
    title = title.encode('ascii', 'ignore').decode('ascii')
    title = title.strip().lower()
    title = re.sub(r'\s+', '', title)  # Remove all whitespace
    title = title.translate(str.maketrans('', '', string.punctuation))
    return title

print("normalize_title function defined...")

def get_all_titles(categories: Dict[str, CategoryInfo]) -> Set[str]:
    all_titles = set()
    for category in categories.values():
        all_titles.update(normalize_title(title) for title in category.titles)
    return all_titles

print("get_all_titles function defined...")

def get_titles_from_json_file(file_path: str) -> Set[str]:
    print(f"Reading titles from {file_path}...")
    with open(file_path, 'r') as file:
        data = json.load(file)
    return set(normalize_title(title) for title in data.get('titles', []))

print("get_titles_from_json_file function defined...")

def is_similar(title1: str, title2: str, threshold: float = 0.6) -> bool:
    return SequenceMatcher(None, title1, title2).ratio() > threshold

print("is_similar function defined...")

def find_similar_titles(set1: Set[str], set2: Set[str], threshold: float = 0.8) -> Set[str]:
    similar_titles = set()
    for title1 in set1:
        for title2 in set2:
            if is_similar(title1, title2, threshold):
                similar_titles.add(title1)
                break
    return similar_titles

print("find_similar_titles function defined...")

# def find_contained_titles(set1: Set[str], set2: Set[str]) -> Set[str]:
#     contained_titles = set()
#     for title1 in set1:
#         for title2 in set2:
#             if title1 in title2 or title2 in title1:
#                 contained_titles.add(title1)
#                 break
#     return contained_titles

print("find_contained_titles function defined...")

def second_pass(dict_to_write: Dict) -> Dict:
    set1 = list(set(dict_to_write["titles_only_in_processed"]))
    set2 = list(set(dict_to_write["titles_only_in_existing"]))
    
    for title in set1:
        for title2 in set2:
            if title in title2 or title2 in title:
                set1.remove(title)
                set2.remove(title2)
                
    new_combined_titles = set(dict_to_write["combined_titles"])
    new_combined_titles_to_remove = set()
    
    combined_set = set(dict_to_write["processed_categories_titles"]).union(new_combined_titles)
    
    # for title in new_combined_titles:
    #     for title2 in combined_set:
    #         if title2 in title or title in title2:
    #             new_combined_titles_to_remove.add(title2)
    
    new_combined_titles -= new_combined_titles_to_remove

    return {"processed_categories_titles": dict_to_write["processed_categories_titles"],"titles_only_in_processed": set1, "titles_only_in_existing": set2, "combined_titles": list(new_combined_titles), "combined_titles_num": len(list(new_combined_titles))}
    

def main():
    print("Starting main function...")
    
    print("Reading processed_category_data.json...")
    with open('PythonCode/Utilities/processed_category_data.json', 'r') as file:
        data = json.load(file)

    print("Converting data to CategoryInfo objects...")
    categories = {name: dict_to_category_info(info) for name, info in data.items()}

    print("Getting all titles from processed category data...")
    titles_from_processed_category_data = get_all_titles(categories)
    dict_to_write = {}
    dict_to_write["processed_categories_titles"] = list(titles_from_processed_category_data)

    print("Getting titles from existingTitles_missingCitations_missingArticlesTitles.json...")
    titles_from_existing_titles_missing_citations_missing_articles_titles = get_titles_from_json_file('assets/json_data/output_verification_using_dm/existingTitles_missingCitations_missingArticlesTitles.json')
    
    combined_titles = titles_from_processed_category_data.union(titles_from_existing_titles_missing_citations_missing_articles_titles)
    combined_titles_to_remove = set()
    
    for title in titles_from_processed_category_data:
        if title in combined_titles:
            
            combined_titles_to_remove.add(title)
    
    combined_titles -= combined_titles_to_remove
    combined_titles_to_remove.clear()
    
    for i in range(len(list(combined_titles))):
        for j in range(i + 1, len(list(combined_titles))):
            if is_similar(list(combined_titles)[i], list(combined_titles)[j]):
                combined_titles_to_remove.add(list(combined_titles)[j])
    
    combined_titles -= combined_titles_to_remove
    
    
    print("Finding similar titles...")
    similar_titles_in_processed = find_similar_titles(titles_from_processed_category_data, titles_from_existing_titles_missing_citations_missing_articles_titles)
    similar_titles_in_existing = find_similar_titles(titles_from_existing_titles_missing_citations_missing_articles_titles, titles_from_processed_category_data)

    print("Calculating titles only in processed category data...")
    titles_only_in_processed = titles_from_processed_category_data - similar_titles_in_existing
    
    print("Calculating titles only in existing titles missing citations missing articles titles...")
    titles_only_in_existing = titles_from_existing_titles_missing_citations_missing_articles_titles - similar_titles_in_processed
    
    print("Titles only in processed category data:", titles_only_in_processed)
    print("Titles only in existing titles missing citations missing articles titles:", titles_only_in_existing)
    
    print("Preparing dictionary to write...")

    dict_to_write["titles_only_in_processed"] = list(titles_only_in_processed)
    dict_to_write["titles_only_in_existing"] = list(titles_only_in_existing)
    dict_to_write["combined_titles"] = list(combined_titles)
    
    dict_to_write = second_pass(dict_to_write)
    dict_to_write["combined_titles_num"] = len(dict_to_write["combined_titles"])
    
    print("Writing results to titles_comparison.json...")
    with open('assets/json_data/output_verification_using_dm/titles_comparison.json', 'w') as file:
        json.dump(dict_to_write, file, indent=2)

    print("Main function completed.")

if __name__ == "__main__":
    main()
    print("Program finished.")