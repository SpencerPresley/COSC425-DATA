import ijson
import json
import sys
import os
from unidecode import unidecode
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from academic_metrics.strategies import StrategyFactory
from academic_metrics.utils import WarningManager, Utilities, FileHandler
from academic_metrics.enums import AttributeTypes

def clean_unicode_escapes(text):
    clean_text = unidecode(text)
    return clean_text

def get_crossref_ab_title(file_path: str, output_file_path: str, utils: Utilities):
    items = ijson.items(open(file_path, "r"), "item")
    paper_dict = {}
    for item in items:
        abstract = utils.get_attributes(item, [AttributeTypes.CROSSREF_ABSTRACT])[
            AttributeTypes.CROSSREF_ABSTRACT
        ][1]
        #abstract = abstract[1]
        title_list = utils.get_attributes(item, [AttributeTypes.CROSSREF_TITLE])[
            AttributeTypes.CROSSREF_TITLE
        ][1]
        # Ensure title_list is a list
        if not isinstance(title_list, list):
            title_list = [title_list]
        title = clean_unicode_escapes(title_list[0])
        if abstract != None and abstract != "":
            paper_dict[title] = clean_unicode_escapes(abstract)
        else:
            print(title)
    
    with open(output_file_path, "w") as file:
        json.dump(paper_dict, file, indent=4)


if __name__ == "__main__":
    utils = Utilities(strategy_factory=StrategyFactory, warning_manager=WarningManager)
    file_path = "fullData.json"
    output_file_path = "title-abstract.json"
    get_crossref_ab_title(file_path, output_file_path, utils)
