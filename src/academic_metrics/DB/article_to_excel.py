import pandas as pd

# pd.set_option('display.max_columns', None)  # Show all columns
# pd.set_option('display.width', None)       # Show all columns

df = pd.read_json("category_data.json")

df.to_excel("category_data.xlsx", index=False)

df = pd.read_json("article_data.json")

df.to_excel("article_data.xlsx", index=False)

df = pd.read_json("faculty_data.json")

df.to_excel("faculty_data.xlsx", index=False)
