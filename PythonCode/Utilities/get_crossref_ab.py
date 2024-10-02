import ijson
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utilities import Utilities
from enums import AttributeTypes

def get_crossref_ab(file_path: str, output_file_path: str, utils: Utilities):
    items = ijson.items(open(file_path, 'r'), 'item')
    abstracts = []
    for item in items:
        abstract = utils.get_attributes(item, [AttributeTypes.CROSSREF_ABSTRACT])[AttributeTypes.CROSSREF_ABSTRACT][1]
        if abstract != None and abstract != "":
            abstracts.append(abstract)
    
    with open(output_file_path, "w") as file:
        json.dump(abstracts, file, indent=4)
        
if __name__ == "__main__":
    utils = Utilities()
    file_path = "paper-doi-list.json"
    output_file_path = "paper-abstracts-list.json"
    get_crossref_ab(file_path, output_file_path, utils)