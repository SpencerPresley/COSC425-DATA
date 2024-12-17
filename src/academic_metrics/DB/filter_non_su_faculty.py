import json

with open("article_data.json", "r") as file:
    article_data = json.load(file)

with open("category_data.json", "r") as file:
    category_data = json.load(file)

non_su_faculty = set()
non_su_departments = set()

for article in article_data:
    faculty_affiles = article["faculty_affiliations"]
    for faculty, affiliations in faculty_affiles.items():
        for affiliation in affiliations:
            if "Salisbury University" not in affiliation:
                non_su_faculty.add(faculty)
                non_su_departments.add(affiliation)


# Update article data by removing non-SU faculty out of faculty_members and faculty_affiliations
for article in article_data:
    article["faculty_members"] = [
        faculty
        for faculty in article["faculty_members"]
        if faculty not in non_su_faculty
    ]
    article["faculty_affiliations"] = {
        faculty: affiliations
        for faculty, affiliations in article["faculty_affiliations"].items()
        if faculty not in non_su_faculty
    }

# Update category data faculty lists by removing non-SU faculty
for category in category_data:
    category["faculty"] = [
        faculty for faculty in category["faculty"] if faculty not in non_su_faculty
    ]

    # Update faculty_count
    category["faculty_count"] = len(category["faculty"])

    # Update departments to remove the affiliations from the non-SU faculty
    category["departments"] = [
        department
        for department in category["departments"]
        if department not in non_su_departments
    ]

    # Update department_count
    category["department_count"] = len(category["departments"])

with open("article_data.json", "w") as file:
    json.dump(article_data, file, indent=4)

with open("category_data.json", "w") as file:
    json.dump(category_data, file, indent=4)
