import ijson
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utilities import Utilities

def get_crossref_ab(file_path: str, output_file_path: str, utils: Utilities):
    items = ijson.items(open(file_path, 'r'), 'item')
    authors = []
    for item in items:
        authors.extend(utils.get_attributes(item, ['crossref-authors'])['crossref-authors'][1])

    
    with open(output_file_path, "w") as file:
        json.dump(authors, file, indent=4)

if __name__ == "__main__":
    utils = Utilities()
    file_path = "paper-doi-list.json"
    output_file_path = "paper-authors-list.json"
    get_crossref_ab(file_path, output_file_path, utils)