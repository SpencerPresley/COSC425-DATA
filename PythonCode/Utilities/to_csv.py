import os
import pandas as pd
import json


def load_json(file_path):
    with open(file_path, "r") as file:
        return json.load(file)


def create_general_info_sheet(data, writer):
    general_info = {
        "Category": [],
        "URL": [],
        "Faculty Count": [],
        "Department Count": [],
        "Article Count": [],
        "Total Citations": [],
        "Citation Average": [],
    }

    for category, category_info in data.items():
        general_info["Category"].append(category)
        general_info["URL"].append(
            "https://cosc425-site.vercel.app/categories/category/"
            + category_info["url"]
        )
        general_info["Faculty Count"].append(category_info["faculty_count"])
        general_info["Department Count"].append(category_info["department_count"])
        general_info["Article Count"].append(category_info["article_count"])
        general_info["Total Citations"].append(category_info["tc_count"])
        general_info["Citation Average"].append(category_info["citation_average"])

    df = pd.DataFrame(general_info)
    print("General Info DataFrame:")
    print(df.head())
    print("Shape:", df.shape)
    df.to_excel(writer, sheet_name="General Info", index=False)


def create_list_sheet(data, writer, sheet_name, list_key):
    expanded_list = {
        "Category": [],
        "item": [],
    }

    for category, details in data.items():
        if list_key in details:
            for item in details[list_key]:
                expanded_list["Category"].append(category)
                expanded_list["item"].append(item)

    df = pd.DataFrame(expanded_list)
    print(f"{sheet_name} DataFrame:")
    print(df.head())
    print("Shape:", df.shape)
    df.to_excel(writer, sheet_name=sheet_name, index=False)


def main():
    file_path = (
        "/Users/spencerpresley/COSC425-MAIN/backend/TextAnalysis/output_data.json"
    )
    data = load_json(file_path)
    print(data)
    input("Press Enter to continue...")

    output_file = "SU_Category_Data_Themes.xlsx"

    # Context manager to handle Excel writer
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        create_general_info_sheet(data, writer)
        create_list_sheet(data, writer, "Faculty Members", "faculty")
        create_list_sheet(data, writer, "Departments", "departments")
        create_list_sheet(data, writer, "Article Titles", "titles")
        create_list_sheet(data, writer, "Research Themes", "themes")

    # Check file size to confirm data was written
    file_size = os.path.getsize(output_file)
    print(f"Generated file size: {file_size} bytes")


if __name__ == "__main__":
    main()
