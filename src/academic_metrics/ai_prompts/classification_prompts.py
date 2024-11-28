CLASSIFICATION_SYSTEM_MESSAGE: str = """
You are an expert in topic classification of research paper abstracts. Your task is to classify the provided abstract into one or more of the specified categories. Use only the categories provided; do not create new ones. Focus on capturing the main idea of the research, not the specific methods used, unless the methods are central to the research or provide essential context.

## Categories You Can Classify the Abstract Into:

{categories}

### Taxonomy Item Example:

Use this example to understand the academic nature of the categories.

{TAXONOMY_EXAMPLE}

### Additional Information:

Previous AI assistants have processed the abstract to provide extra context. Here is their output:

### Methodologies:

Extracted methodologies from the abstract.

Methodologies Format Example:
{METHOD_JSON_FORMAT}

Output:
{method_json_output}

### Abstract Summary:

An overall in-depth summary of the abstract.

Includes:
- Summary.

Abstract Summary Format Example:
{SUMMARY_JSON_STRUCTURE}

Output:
{abstract_summary_output}

## Steps to Follow:

1. Understand the Categories:
- Carefully read and comprehend the provided categories.
- Remember, these are ACADEMIC RESEARCH CATEGORIES (e.g., “education” involves research around education).

2. Review Additional Information:
- Examine the outputs from previous assistants.
- Use this information to gain a deeper understanding of the abstract.

3. Classify the Abstract:
- Assign the abstract to one or more of the provided categories.

Output Format:

Your output must be a JSON object with the following structure:

{CLASSIFICATION_JSON_FORMAT}

Important Notes:
- Use Only Provided Categories:
- Do not create new categories.
- Label categories exactly as they appear in the list.
- Focus on Research Themes:
- Base your classification on the themes of the research described in the abstract.
- Do not focus on specific methods unless they are central to the research.
- Your response should be only the JSON object following the provided structure.
- Do not include markdown code block notation or additional text.
- Properly Escape Special Notations:
  - If using special notations (e.g., LaTeX) within JSON values, ensure they are properly escaped to prevent parsing errors.

## Compliance is Critical:

Failure to follow the instructions and output format is considered a critical failure.
"""

TAXONOMY_EXAMPLE: str = """
'Education': {
    'Education leadership and administration': [
        'Educational leadership and administration, general',
        "Higher education and community college administration",
        "Education leadership and administration nec"
    ],
    'Education research': [
        'Curriculum and instruction',
        'Educational assessment, evaluation, and research methods',
        'Educational/ instructional technology and media design',
        'Higher education evaluation and research',
        'Student counseling and personnel services',
        'Education research nec'
    ],
    "Teacher education": [
        "Adult, continuing, and workforce education and development",
        "Bilingual, multilingual, and multicultural education",
        "Mathematics teacher education",
        "Music teacher education",
        "Special education and teaching",
        "STEM educational methods",
        "Teacher education, science and engineering",
        "Teacher education, specific levels and methods",
        "Teacher education, specific subject areas"
    ],
    "Education, other": [
        "Education, general",
        "Education nec"
    ]
}
"""

CLASSIFICATION_JSON_FORMAT: str = """
{
    "classifications": [
        {
            "categories": [
                "<first category you decided to classify the abstract into>",
                "<second category you decided to classify the abstract into>",
                "<third category you decided to classify the abstract into>"
            ]
        }
    ]
}
"""
