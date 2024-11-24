import json

with open("example_req.json", "r") as file:
    data = json.load(file)

with open("reformatted.json", "w") as file:
    json.dump(data, file, indent=4)
