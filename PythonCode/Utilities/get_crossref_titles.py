import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utilities import Utilities  
import json
import ijson
from enums import AttributeTypes
def get_crossref_titles(file_path: str, output_file_path: str, utils: Utilities):
    items = ijson.items(open(file_path, 'r'), 'item')
    title_dict = {}
    titles = []
    for item in items:
        title_list = utils.get_attributes(item, [AttributeTypes.CROSSREF_TITLE])[AttributeTypes.CROSSREF_TITLE][1]
        # Ensure title_list is a list
        if not isinstance(title_list, list):
            title_list = [title_list]
        for title in title_list:
            print(title)
            titles.append(title)
    title_dict["CrossrefTitles"] = titles
    with open(output_file_path, "w") as file:
        json.dump(title_dict, file, indent=4)

if __name__ == "__main__":
    utils = Utilities()
    file_path = "paper-doi-list.json"
    output_file_path = "paper-titles-list.json"
    get_crossref_titles(file_path, output_file_path, utils)