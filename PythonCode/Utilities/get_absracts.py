import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utilities import Utilities  
import json
from enums import AttributeTypes
if __name__ == "__main__":
    split_files_path = './split_files'
    utilities = Utilities()
    all_abstracts = []
    for file in os.listdir(split_files_path):
        with open(os.path.join(split_files_path, file), 'r') as f:
            text = f.read()
            abstract = utilities.get_attributes(text, [AttributeTypes.ABSTRACT])[AttributeTypes.ABSTRACT][1]
            all_abstracts.append(abstract)
            print(abstract)
    abstract_dict = {'abstracts': all_abstracts}
    with open('ALL_ABSTRACTS.json', 'w') as f:
        json.dump(abstract_dict, f, indent=4)