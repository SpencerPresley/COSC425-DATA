
import json

with open('abstracts_to_categories.json', 'r') as f:
    data = json.load(fp=f)


print(len(data.keys()))