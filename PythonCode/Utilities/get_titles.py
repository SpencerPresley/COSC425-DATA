import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utilities import Utilities  


if __name__ == "__main__":
    split_files_path = './split_files'
    utilities = Utilities()
    all_titles = []
    for file in os.listdir(split_files_path):
        with open(os.path.join(split_files_path, file), 'r') as f:
            text = f.read()
            title = utilities.get_attributes(text, ['title'])['title'][1]
            all_titles.append(title)
            print(title)
    with open('ALL_TITLES.txt', 'w') as f:
        for title in all_titles:
            f.write(title + '\n') 