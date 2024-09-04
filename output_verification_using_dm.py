# Verifies output of pipeline by checking the digimtal meaures data in assets/json_data/ and seeing if we have all of those articles based on titles.

import json
import os
import re

needs_second_pass = []

def extract_title(citation):
    # Extract title from a citation key
    match = re.search(r'\(\d{4}\)\.\s*(.*?)\.\s', citation)
    if match:
        return match.group(1).strip()
    else:
        needs_second_pass.append(citation)
        return None

def process_json_file(file_path):
    titles = []
    with open(file_path, 'r') as file:
        data = json.load(file)
        for department in data.values():
            for item in department:
                if isinstance(item, dict) and "Citation" in item:
                    title = extract_title(item["Citation"])
                    if title:
                        titles.append(title)

    return {"titles": titles}

def main():
    json_data_dir = "assets/json_data"
    titles = {}
    
    for filename in os.listdir(json_data_dir):
        if filename.endswith(".json"):
            file_path = os.path.join(json_data_dir, filename)
            result = process_json_file(file_path)
            for key, value in result.items():
                if key not in titles:
                    titles[key] = []
                titles[key].extend(value)
    
    output_dir = "assets/json_data/output_verification_using_dm"
    os.makedirs(output_dir, exist_ok=True)
    
    output_file_path = os.path.join(output_dir, "existingTitles_missingCitations_missingArticlesTitles.json")
    with open(output_file_path, "w") as output_file:
        json.dump(titles, output_file, indent=2)
    
    print(f"Output saved to: {output_file_path}")

if __name__ == "__main__":
    main()
    with open("assets/json_data/output_verification_using_dm/needs_second_pass.json", "w") as output_file:
        json.dump(needs_second_pass, output_file, indent=2)