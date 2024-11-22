import json
import os
from typing import Dict, Any, List, cast
from dotenv import load_dotenv
from academic_metrics.DB import DatabaseWrapper


def validate_category_item(item: Dict[str, Any], index: int) -> List[str]:
    """Validate a single category item for potential issues."""
    errors = []

    # Required fields
    required_fields = [
        "_id",
        "url",
        "category_name",
        "faculty",
        "departments",
        "titles",
        "doi_list",
        "themes",
    ]

    # Check for missing required fields
    for field in required_fields:
        if field not in item:
            errors.append(f"Item {index}: Missing required field '{field}'")

    # Check for None values in required fields
    for field in required_fields:
        if field in item and item[field] is None:
            errors.append(f"Item {index}: Field '{field}' is None")

    # Check numeric fields
    numeric_fields = [
        "faculty_count",
        "department_count",
        "article_count",
        "tc_count",
        "citation_average",
    ]
    for field in numeric_fields:
        if field in item:
            if not isinstance(item[field], (int, float)):
                errors.append(
                    f"Item {index}: Field '{field}' is not numeric: {type(item[field])}"
                )

    # Check list fields
    list_fields = ["faculty", "departments", "titles", "doi_list", "themes"]
    for field in list_fields:
        if field in item and not isinstance(item[field], list):
            errors.append(
                f"Item {index}: Field '{field}' is not a list: {type(item[field])}"
            )

    return errors


def gather_error_data(data: List[Dict[str, Any]]) -> List[str]:
    if not isinstance(cast(Any, data), list):
        print("Data is not a list")
        raise ValueError("Data is not a list")

    all_errors = []
    for idx, item in enumerate(data):
        errors = validate_category_item(item, idx)
        if errors:
            all_errors.extend(errors)

    if all_errors:
        print("\nValidation errors found:")
        for error in all_errors:
            print(f"- {error}")
    else:
        print("\nNo validation errors found in category data")

    print("\nQuick stats:")
    print(f"Total categories: {len(data)}")
    print(
        f"Unique faculty: {len(set([f for item in data for f in item.get('faculty', [])]))}"
    )
    print(
        f"Unique departments: {len(set([d for item in data for d in item.get('departments', [])]))}"
    )
    print(
        f"Unique DOIs: {len(set([d for item in data for d in item.get('doi_list', [])]))}"
    )


def main(category_data: List[Dict[str, Any]], mongo_url: str) -> None:
    if not mongo_url:
        raise ValueError("MONGODB_URL not found in environment variables")

    db = DatabaseWrapper(db_name="Site_Data", mongo_url=mongo_url)

    print(f"Attempting to insert {len(category_data)} categories into the database")

    try:
        db.insert_categories(category_data)
        print("Insertion successful")
    except Exception as e:
        print(f"Error inserting categories: {str(e)}")
        db.close_connection()
        raise e
    finally:
        try:
            db.close_connection()
        except Exception as e:
            print(f"Error closing database connection: {str(e)}")
            raise e


if __name__ == "__main__":
    from academic_metrics.constants import OUTPUT_FILES_DIR_PATH

    load_dotenv()
    live_mongodb_url = os.getenv("MONGODB_URL")
    local_mongodb_url = os.getenv("LOCAL_MONGODB_URL")
    with open(OUTPUT_FILES_DIR_PATH / "test_processed_category_data.json", "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error loading JSON: {e}")
            raise e

    print(f"\n\n{'=' * 50}LIVE MONGO RUN{'=' * 50}\n\n")
    gather_error_data(data)
    main(data, live_mongodb_url)
    print(f"\n\n{'=' * 50}LOCAL MONGO RUN{'=' * 50}\n\n")
    gather_error_data(data)
    main(data, local_mongodb_url)
