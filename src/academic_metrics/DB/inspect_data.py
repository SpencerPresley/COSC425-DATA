import json
from pathlib import Path

# Get the current file's directory
current_dir = Path(__file__).parent

# Load the JSON data using proper path
json_path = current_dir / "category_data.json"
with open(json_path, "r") as f:
    data = json.load(f)

# Get the first item
first_item = data[0]

# Remove specified keys
keys_to_remove = [
    "_id",
    "url",
    "faculty",
    "departments",
    "titles",
    "doi_list",
    "themes",
]
for key in keys_to_remove:
    first_item.pop(key, None)

# Print the cleaned data with nice formatting
print(json.dumps(first_item, indent=2))
