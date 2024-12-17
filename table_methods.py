import matplotlib.pyplot as plt
import pandas as pd
import json
from textwrap import wrap

# Load the JSON data
with open(
    "src/other/testing_data/method_extraction/method_json_output_0.json", "r"
) as file:
    json_data = json.load(file)

# Extract methods and their details
methods = json_data["methods"]
method_details = []

for method in methods:
    details = json_data[method]
    method_details.append(
        {
            "Method": method,
            "Reasoning": details["reasoning"],
            "Confidence": f"{details['confidence_score']:.2f}",
        }
    )

# Create a DataFrame
df = pd.DataFrame(method_details)


# Function to wrap text
def wrap_text(text, width=30):
    return "\n".join(wrap(text, width))


# Wrap text in DataFrame
df["Method"] = df["Method"].apply(lambda x: wrap_text(x, width=20))
df["Reasoning"] = df["Reasoning"].apply(lambda x: wrap_text(x, width=40))

# Create figure and axis
fig, ax = plt.subplots(figsize=(16, 6))  # Width matches typical slide dimensions

# Hide axes
ax.axis("tight")
ax.axis("off")

# Create table
table = ax.table(
    cellText=df.values,
    colLabels=df.columns,
    cellLoc="left",
    loc="center",
    colWidths=[0.2, 0.7, 0.1],
)

# Style the table
table.auto_set_font_size(False)
table.set_fontsize(11)
table.scale(1.2, 2.5)  # Increased row height for wrapped text

# Color header row
header_cells = [table[0, i] for i in range(len(df.columns))]
for cell in header_cells:
    cell.set_facecolor("#4472C4")
    cell.set_text_props(color="white")
    cell.set_fontsize(12)

# Adjust layout and save
plt.title("Methods Analysis", pad=20, fontsize=14)
plt.tight_layout()
plt.savefig("methods_table.png", dpi=300, bbox_inches="tight")
plt.show()
