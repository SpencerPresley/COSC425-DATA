# ResearchTaxonomy Class Documentation

The `ResearchTaxonomy` class is designed to generate a taxonomy of research categories based on abstracts. This class interfaces with the OpenAI API to analyze text and categorize it into structured taxonomy JSON format. The class is useful for researchers and organizations looking to categorize and index abstracts for easier retrieval and analysis.

## Constructor

### `__init__(self, prompt_num=0, file_name="Taxonomy.json", data_needed=False)`

Initializes a new instance of the `ResearchTaxonomy` class.

#### Parameters:
- `prompt_num` (int): The index of the prompt to use from the predefined list.
- `file_name` (str): The name of the file where the taxonomy will be saved.
- `data_needed` (bool): Determines whether to immediately generate taxonomy upon initialization.

#### Functionality:
- Prompts the user to enter the path to the abstract file.
- Loads the abstracts from the specified file.
- Optionally generates a taxonomy of the abstracts if `data_needed` is True.

## Methods

### `get_response(self, messages, model='gpt-3.5-turbo', temperature=0.5, max_tokens=1000)`

Sends a request to the OpenAI API and retrieves the response.

#### Parameters:
- `messages` (list of dict): A list of message dictionaries formatted for the OpenAI API.
- `model` (str): The model identifier to use for the API call.
- `temperature` (float): The temperature setting for the AI's responses.
- `max_tokens` (int): The maximum number of tokens in the response.

#### Returns:
- The API response content in human-readable format.

### `get_taxonomy_abstracts(self)`

Processes all abstracts to create a taxonomy and outputs it to a JSON file.

#### Functionality:
- Iterates over each abstract, uses the API to generate taxonomy data, and collects the results.
- Writes the complete taxonomy to a specified file.

### `get_individual_taxonomy(self, abstractData, title, outputType='file')`

Generates the taxonomy for an individual abstract.

#### Parameters:
- `abstractData` (str): The abstract text.
- `title` (str): The title of the abstract.
- `outputType` (str): Determines the output method (file or other).

#### Returns:
- The taxonomy data as a JSON object.

### `get_categories(self)`

Collects and returns a comprehensive set of categories based on all abstracts.

#### Returns:
- A dictionary containing lists of upper, mid, and theme level categories.

### `add_theme_taxonomy(self, fileName)`

Adds thematic data to an existing taxonomy.

#### Parameters:
- `fileName` (str): The name of the file containing the category dictionaries.

#### Functionality:
- Enhances an existing taxonomy with additional thematic data from a provided JSON file.
