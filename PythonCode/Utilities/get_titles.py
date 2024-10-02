import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utilities import Utilities  
import json
from enums import AttributeTypes

if __name__ == "__main__":
    split_files_path = './split_files_2'
    utilities = Utilities()
    all_titles = []
    for file in os.listdir(split_files_path):
        with open(os.path.join(split_files_path, file), 'r') as f:
            text = f.read()
            title = utilities.get_attributes(text, [AttributeTypes.TITLE])[AttributeTypes.TITLE][1]
            if title is None:
                print(file)
                input("Press Enter to continue...")
                continue
            all_titles.append(title)
    with open('2024_titles.json', 'w') as f:
        titles_dict = {
            "year": 2024,
            "titles_count": len(all_titles),
            "titles": all_titles
        }
        json.dump(titles_dict, f, indent=4)