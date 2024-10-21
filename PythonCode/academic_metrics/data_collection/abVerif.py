import json
import requests
import scrape

# Load the data from the JSON file
with open("fullData.json", "r") as f:
    data = json.load(fp=f)

# Identify DOIs for entries that are missing abstracts
query_dict = {
    elem["DOI"]: elem["URL"] for elem in data if elem.get("abstract", "NA") == "NA"
}


data = scrape.AI_get_missing_abstracts(query_dict)


with open('missingAbstractsTest.json', 'w') as f:
    json.dump(data, fp=f, indent=4)
