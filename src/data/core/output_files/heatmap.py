import numpy as np
import pandas as pd
import json
import seaborn as sns
import matplotlib.pyplot as plt

# Load data
import numpy as np
import pandas as pd
import json
import seaborn as sns
import matplotlib.pyplot as plt

# Load data
with open("test_processed_crossref_article_stats_obj_data.json", "r") as f:
    data = json.load(f)

# Get only Salisbury faculty members
salisbury_faculty = set()
for article in data.values():
    for faculty, affiliation in article["faculty_affiliations"].items():
        if "Salisbury" in affiliation and affiliation != "Salisbury University":
            salisbury_faculty.add(faculty)

salisbury_faculty = list(
    salisbury_faculty
)  # Should be ['KwangWook Gang', 'Minseok Park', 'Christy H. Weer']

# Create collaboration matrix for Salisbury faculty
collaboration_matrix = pd.DataFrame(
    0, index=salisbury_faculty, columns=salisbury_faculty
)

# Fill collaboration matrix
for article in data.values():
    faculty_in_paper = [f for f in article["faculty_members"] if f in salisbury_faculty]


# Create heatmap
plt.figure(figsize=(12, 10))
sns.heatmap(
    collaboration_matrix,
    annot=True,
    fmt=".0f",
    cmap="YlOrRd",
    cbar_kws={"label": "Number of Collaborations"},
)
plt.title("Faculty Collaboration Network")
plt.tight_layout()
plt.savefig("faculty_collaboration_heatmap.png")
plt.close()

# Create affiliation-citation matrix
affiliations = set()
for article in data.values():
    affiliations.update(article["faculty_affiliations"].values())
affiliations = list(affiliations)

affiliation_citation_matrix = pd.DataFrame(
    0, index=affiliations, columns=["article_count", "total_citations"]
)

for article in data.values():
    tc_count = article["tc_count"]
    for affiliation in article["faculty_affiliations"].values():
        if affiliation != "Salisbury University" and "Salisbury" in affiliation:
            affiliation_citation_matrix.loc[affiliation, "article_count"] += 1
            affiliation_citation_matrix.loc[affiliation, "total_citations"] += tc_count

# Create heatmap for affiliations
plt.figure(figsize=(10, 8))
sns.heatmap(
    affiliation_citation_matrix,
    annot=True,
    fmt=".0f",
    cmap="YlOrRd",
    cbar_kws={"label": "Count"},
)
plt.title("Institution Impact: Articles vs Citations")
plt.tight_layout()
plt.savefig("institution_impact_heatmap.png")
plt.close()
