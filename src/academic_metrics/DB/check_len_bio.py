import json

with open("category_data.json", "r") as file:
    data = json.load(file)

for item in data:
    if item["category_name"] == "Biochemistry, biophysics, and molecular biology":
        print(item["faculty_count"])
        print(len(item["faculty"]))
        break
