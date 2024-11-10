import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import networkx as nx
import json
from collections import defaultdict

# Read data
with open("test_processed_faculty_stats_data.json", "r") as f:
    faculty_data = json.load(f)
with open("test_processed_article_stats_data.json", "r") as f:
    article_data = json.load(f)
with open("test_processed_category_data.json", "r") as f:
    category_data = json.load(f)

# Style selection
for i, style in enumerate(plt.style.available):
    print(f"{i}: {style}")
style = input("Select a style: ")
plt.style.use(plt.style.available[int(style)])

# 1. Faculty Collaboration Network
plt.figure(figsize=(10, 10))  # Adjusted for MacBook M1 Air screen
G = nx.Graph()

# Create collaboration mapping
collaborations = defaultdict(int)
faculty_citations = defaultdict(int)
faculty_dept = {}

for category in faculty_data.values():
    for faculty, stats in category.get("faculty_stats", {}).items():
        faculty_citations[faculty] = stats["total_citations"]
        faculty_dept[faculty] = stats["department_affiliations"].split(",")[0]

        # Find collaborations through shared papers
        for paper_title in stats["citation_map"]["article_citation_map"].keys():
            for other_faculty, other_stats in category.get("faculty_stats", {}).items():
                if (
                    faculty != other_faculty
                    and paper_title
                    in other_stats["citation_map"]["article_citation_map"]
                ):
                    collaborations[
                        (min(faculty, other_faculty), max(faculty, other_faculty))
                    ] += 1

# Create network
for (faculty1, faculty2), weight in collaborations.items():
    G.add_edge(faculty1, faculty2, weight=weight)

# Add nodes with citation counts
for faculty in faculty_citations:
    G.add_node(
        faculty, citations=faculty_citations[faculty], dept=faculty_dept[faculty]
    )

# Draw network
pos = nx.spring_layout(G, k=3, iterations=50)  # Increased k for more spread
node_sizes = [
    max(200, G.nodes[node]["citations"] * 10) for node in G.nodes()
]  # Minimum size of 200
edge_weights = [
    max(1, G.edges[edge]["weight"]) for edge in G.edges()
]  # Minimum weight of 1

# Color nodes by department
dept_colors = {
    dept: plt.cm.tab20(i) for i, dept in enumerate(set(faculty_dept.values()))
}
node_colors = [dept_colors[G.nodes[node]["dept"]] for node in G.nodes()]

# Create legend for departments
legend_elements = [
    plt.Line2D(
        [0], [0], marker="o", color="w", markerfacecolor=color, label=dept, markersize=8
    )
    for dept, color in dept_colors.items()
]

nx.draw_networkx_nodes(G, pos, node_size=node_sizes, node_color=node_colors, alpha=0.7)
nx.draw_networkx_edges(G, pos, width=edge_weights, alpha=0.3)
nx.draw_networkx_labels(G, pos, font_size=6)

plt.title(
    "Research Collaboration Network\n\n"
    + "Node size represents citation impact\n"
    + "Edge thickness shows number of collaborations\n"
    + "Colors indicate department affiliation",
    pad=20,
    fontsize=10,
)
plt.legend(handles=legend_elements, loc="center left", bbox_to_anchor=(1, 0.5))
plt.axis("off")
plt.tight_layout()
plt.show()

# 2. Department Impact Matrix
departments = defaultdict(lambda: {"papers": 0, "citations": 0, "faculty": set()})

for category in faculty_data.values():
    for faculty, stats in category.get("faculty_stats", {}).items():
        dept = stats["department_affiliations"].split(",")[0]
        departments[dept]["papers"] += stats["article_count"]
        departments[dept]["citations"] += stats["total_citations"]
        departments[dept]["faculty"].add(faculty)

# Create department metrics DataFrame
dept_metrics = pd.DataFrame(
    {
        "Total Papers": {k: v["papers"] for k, v in departments.items()},
        "Total Citations": {k: v["citations"] for k, v in departments.items()},
        "Faculty Count": {k: len(v["faculty"]) for k, v in departments.items()},
        "Citations per Paper": {
            k: round(v["citations"] / v["papers"], 2) if v["papers"] > 0 else 0
            for k, v in departments.items()
        },
    }
)

# Plot department impact matrix
plt.figure(figsize=(12, 8))  # Adjusted for MacBook M1 Air screen
dept_metrics_normalized = (dept_metrics - dept_metrics.mean()) / dept_metrics.std()
sns.heatmap(
    dept_metrics_normalized.sort_values("Total Citations", ascending=False).head(15),
    cmap="RdYlBu",
    center=0,
    annot=dept_metrics.sort_values("Total Citations", ascending=False).head(
        15
    ),  # Show actual values
    fmt=".0f",
)  # No decimal places for actual values

plt.title(
    "Department Research Impact Comparison\n\n"
    + "Colors show normalized scores (standard deviations from mean)\n"
    + "Numbers show actual values\n"
    + "Departments sorted by total citations",
    pad=20,
    fontsize=14,
)
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.show()

# 3. Citation Distribution
plt.figure(figsize=(12, 6))  # Adjusted for MacBook M1 Air screen
citations = [
    stats["total_citations"]
    for category in faculty_data.values()
    for stats in category.get("faculty_stats", {}).values()
]

sns.histplot(citations, bins=30, log_scale=True)
plt.title(
    "Distribution of Faculty Citations\n\n"
    + "Shows how many faculty members achieve different citation counts\n"
    + "Log scale used to show full range of impact",
    pad=20,
    fontsize=14,
)
plt.xlabel("Citation Count (log scale)")
plt.ylabel("Number of Faculty Members")

# Add summary statistics
plt.text(
    0.02,
    0.98,
    f"Total Faculty: {len(citations)}\n"
    + f"Median Citations: {int(pd.Series(citations).median())}\n"
    + f"Mean Citations: {int(pd.Series(citations).mean())}\n"
    + f"Max Citations: {int(max(citations))}",
    transform=plt.gca().transAxes,
    verticalalignment="top",
    bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
)

plt.tight_layout()
plt.show()
