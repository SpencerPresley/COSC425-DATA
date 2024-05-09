import json

# Load the JSON data from the file
with open('definition_output.json', 'r') as file:
    data = json.load(file)

# Open a file to write categories that don't have themes
with open('LOGS_categories_without_themes.txt', 'w') as output_file:
    # Loop through each category in the JSON data
    for category, details in data.items():
        # Check if 'themes' key is not present in the category details
        if 'themes' not in details:
            # Write the category name to the file
            output_file.write(category + '\n')

print("Categories without themes have been written to categories_without_themes.txt")