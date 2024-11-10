import json
import pandas as pd
from abstracts import abstracts
import os
import re

ARTICLE_DATA = None
this_directory = os.path.dirname(os.path.abspath(__file__))
output_files_directory = os.path.join(this_directory, "..", "..", "output_files")
print(f"\n\nOutput files directory: {output_files_directory}")
file_name = "test_processed_crossref_article_stats_obj_data.json"
file_path = os.path.join(output_files_directory, file_name)
print(f"\n\nFile path: {file_path}")
with open(file_path, "r") as f:
    ARTICLE_DATA = json.load(f)

print("\nAbstracts in list:")
for i, abstract in enumerate(abstracts):
    print(f"\nAbstract {i} (first 100 chars): {abstract[:100]}...")

print("\nAbstracts in JSON:")
for doi, article in ARTICLE_DATA.items():
    print(f"\nDOI {doi} (first 100 chars): {article['abstract'][:100]}...")


def clean_text(text):
    """Clean text by removing punctuation, extra whitespace, and converting to lowercase"""
    # Remove punctuation and convert to lowercase
    text = re.sub(r"[^\w\s]", "", text.lower())
    # Normalize whitespace
    text = " ".join(text.split())
    return text


def find_article_details(target_abstract):
    """
    Find article details by matching an abstract in the articles data.

    Args:
        target_abstract (str): The abstract to search for
        articles_data (dict): The dictionary containing article data

    Returns:
        dict: Article details including title, faculty members, and DOI
              Returns None if no match is found
    """
    global ARTICLE_DATA
    # Clean up the target abstract
    new_target_abstract = clean_text(target_abstract)

    # Loop through each article
    for doi, article in ARTICLE_DATA.items():
        article_abstract = clean_text(article["abstract"])

        # Print first 100 chars of both abstracts for debugging
        print(f"\nComparing abstracts:")
        print(f"Target  (first 100): {new_target_abstract[:100]}")
        print(f"Article (first 100): {article_abstract[:100]}")

        if article_abstract == new_target_abstract:
            print(f"✅ Found match!")
            return {
                "title": article["title"],
                "faculty_members": article["faculty_members"],
                "doi": doi,
            }

    return None


# Create an absolute path for the output Excel file
output_excel_path = os.path.join(this_directory, "classification_output.xlsx")
print(f"\nWill save Excel file to: {output_excel_path}")

data_rows = []  # Initialize an empty list to hold data rows

with open("classification_results.json", "r") as f:
    classification_results = json.load(f)

# Load the raw_classification_outputs JSON data
with open("raw_classification_outputs.json", "r") as f:
    raw_classification_outputs = json.load(f)

# Open a file to log the output
with open("logs.txt", "w") as log_file:
    # Initialize a list to hold data rows for the DataFrame
    data_rows = []

    # Iterate over each abstract in the classification_results
    for abstract_key, categories in classification_results.items():
        print(f"\nProcessing abstract key: {abstract_key}")

        index = int(abstract_key.split("_")[1])
        abstract_text = abstracts[index]
        abstract_details = find_article_details(abstract_text)

        if abstract_details is None:
            print(f"❌ No article details found for abstract: {abstract_key}")
            continue

        print(f"✅ Processing {abstract_key}:")
        abstract_title = abstract_details["title"]
        abstract_faculty_members = abstract_details["faculty_members"]
        abstract_doi = abstract_details["doi"]

        # Find the corresponding raw data for this abstract
        raw_data = raw_classification_outputs[index]
        print(f"\n\nRaw data: {raw_data}", file=log_file)

        # Iterate over each category in the classification_results
        def traverse_categories(cat_dict, parent_categories):
            for cat_name, sub_cats in cat_dict.items():
                current_categories = parent_categories + [cat_name]
                full_category = ", ".join(current_categories)
                print(f"\n\nTraversing category: {cat_name}", file=log_file)

                # Match the abstract and category in raw_classification_outputs
                category_reasoning = ""
                category_confidence = ""
                for classification in raw_data.get("classifications", []):
                    if abstract_text == classification.get(
                        "abstract"
                    ) and cat_name in classification.get("categories", []):
                        category_reasoning = classification.get("reasoning", "")
                        category_confidence = classification.get("confidence_score", "")
                        break

                # Prepare the data row
                # data_row = {
                #     'Abstract Key': abstract_key,
                #     'Abstract': abstract_text,
                #     'Category': cat_name,
                #     'Parent Categories': ', '.join(parent_categories),
                #     'Reasoning': category_reasoning,
                #     'Confidence Score': category_confidence,
                #     'Reflection': raw_data.get('reflection', ''),
                #     'Feedback': '; '.join([fb.get('feedback', '') for fb in raw_data.get('feedback', [])])
                # }
                data_row = {
                    "Abstract Key": abstract_key,
                    "Title": abstract_title,
                    "Authors": ", ".join(abstract_faculty_members),
                    "DOI": abstract_doi,
                    "Abstract": abstract_text,
                    "Category": cat_name,
                    "Parent Categories": ", ".join(parent_categories),
                    "Themes": (
                        "; ".join(cat_dict.get("themes", []))
                        if not parent_categories
                        else ""
                    ),
                }
                print(f"\n\nData row: {data_row}", file=log_file)
                data_rows.append(data_row)

                if isinstance(sub_cats, dict):
                    # Recurse with the subcategories
                    traverse_categories(sub_cats, current_categories)

        # Start traversing from the top-level categories
        traverse_categories(categories, [])
        print(f"\n\nCurrent number of rows: {len(data_rows)}")

print(f"\nFinal number of rows collected: {len(data_rows)}")


# Create DataFrame and save to Excel
try:
    print("\nCreating DataFrame...")
    df = pd.DataFrame(data_rows)
    print(f"DataFrame created with shape: {df.shape}")

    # Debug: Print column names
    print("\nColumns in DataFrame:")
    print(df.columns.tolist())

    # Debug: Print first few rows
    print("\nFirst few rows of DataFrame:")
    print(df.head())

    print("\nSaving to Excel...")
    # Explicitly set the column order
    columns = [
        "Abstract Key",
        "Title",
        "Authors",
        "DOI",
        "Abstract",
        "Category",
        "Parent Categories",
        "Themes",
    ]
    df = df[columns]  # Reorder columns

    df.to_excel(output_excel_path, index=False, engine="openpyxl")
    print(f"✅ Excel file saved successfully to: {output_excel_path}")

except Exception as e:
    print(f"❌ Error saving Excel file: {str(e)}")

    # Print some debugging info about the data
    print("\nDebugging info:")
    if data_rows:
        print("Sample row data:")
        for key, value in data_rows[0].items():
            print(f"{key}: {value[:100] if isinstance(value, str) else value}")
