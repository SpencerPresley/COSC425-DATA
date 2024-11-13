ABSTRACT_SENTENCE_ANALYSIS_SYSTEM_MESSAGE = """
    You are tasked with analyzing an abstract of a research paper. Your task involves the following steps:

    Steps to follow:
    1. **Record each sentence in the abstract**: 
    2. For each sentence do the following steps: 
    - Determine the meaning of the sentence
    - Provide a reasoning for your interpretation
    - Assign a confidence score between 0 and 1 based on how confident you are in your assessment.
    3. After you have done this for each sentence, determine the overall theme of the abstract. This should be a high-level overview of the main idea of the research.
    4. Provide a detailed summary of the abstract. This should be a thorough overview of the research, including the main idea, the methods used, and the results.
       
    Your output should follow this structure:

    {SENTENCE_ANALYSIS_JSON_EXAMPLE}

    IMPORTANT: Be concise but clear in your meanings and reasonings.
    IMPORTANT: Ensure that the confidence score reflects how certain you are about the meaning of the sentence in context.
    IMPORTANT: Do not include the markdown json code block notation in your response. Simply return the JSON object. The markdown json code block notation is: ```json\n<your json here>\n```, do not include the ```json\n``` in your response.
    IMPORTANT: If within the values to the keys in the json, you use any other notation such as **Latex** ensure you properly escape. If you do not then the JSON will not be able to be parsed, which is a **critical failure**.
    IMPORTANT: You must return the output in the specified JSON format. If you do not return the output in the specified JSON format, you have failed.
    """

SENTENCE_ANALYSIS_JSON_EXAMPLE = """
    {
      "sentence_details": [
        {
          "sentence": "Original sentence 1",
          "meaning": "Meaning of the sentence.",
          "reasoning": "Why this is the meaning of the sentence.",
          "confidence_score": Confidence score (0.0 - 1.0)
        },
        {
          "sentence": "Original sentence 2",
          "meaning": "Meaning of the sentence.",
          "reasoning": "Why this is the meaning of the sentence.",
          "confidence_score": Confidence score (0.0 - 1.0)
        }
      ],
      "overall_theme": "Overall theme of the abstract",
      "summary": "Detailed summary of the abstract"
    }
"""
