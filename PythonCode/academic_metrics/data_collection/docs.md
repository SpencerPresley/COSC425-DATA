# Documentation for Data Collection Scripts

## Table of Contents
1. [Introduction](#introduction)
2. [Scraper](#scraper)
    - [Overview](#overview)
    - [Usage](#usage)
    - [Functions](#functions)
3. [Crossref Wrapper](#crossref-wrapper)
    - [Overview](#overview-1)
    - [Usage](#usage-1)
    - [Functions](#functions-1)
4. [License](#license)
5. [Acknowledgments](#acknowledgments)

## Introduction
This documentation provides an overview and usage instructions for the data collection scripts used in this project. The scripts include a web scraper (`scraper.py`) and a Crossref API wrapper (`crossrefwrapper.py`).

## Scraper

### Overview
The `scraper.py` script is designed to fetch and clean text data from web pages. It uses Selenium for web scraping and BeautifulSoup for parsing HTML content. The script also integrates with OpenAI's API to clean and format the extracted text.

### Usage
To use the scraper, you need to have the required dependencies installed. You can install them using:
```bash
pip install -r requirements.txt
```
Then, you can run the script as follows:
```bash
python scraper.py
```

### Functions

#### `setup_chain(output_list)`
- **Description**: Sets up the chain manager for cleaning the extracted text.
- **Parameters**: 
  - `output_list` (list): List of text elements to be cleaned.
- **Returns**: A dictionary containing the cleaned text.

#### `get_abstract(url)`
- **Description**: Fetches and processes the abstract from a given URL.
- **Parameters**: 
  - `url` (str): The URL of the web page to scrape.
- **Returns**: A dictionary containing the abstract and extra context.

## Crossref Wrapper

### Overview
The `crossrefwrapper.py` script is designed to interact with the Crossref API to fetch metadata for academic papers. It supports asynchronous data fetching and processes the data to include only relevant information.

### Usage
To use the Crossref wrapper, you need to have the required dependencies installed. You can install them using:
```bash
pip install -r requirements.txt
```
Then, you can run the script as follows:
```bash
python crossrefwrapper.py
```

### Functions

#### `__init__(self, base_url, affiliation, from_year, to_year, logger)`
- **Description**: Initializes the CrossrefWrapper class.
- **Parameters**: 
  - `base_url` (str): The base URL for the Crossref API.
  - `affiliation` (str): The affiliation to filter results by.
  - `from_year` (int): The starting year for the data fetch.
  - `to_year` (int): The ending year for the data fetch.
  - `logger` (logging.Logger): Logger instance for logging.

#### `fetch_data(self, session, url, headers, retries, retry_delay)`
- **Description**: Fetches data from the Crossref API.
- **Parameters**: 
  - `session` (aiohttp.ClientSession): The aiohttp session.
  - `url` (str): The URL to fetch data from.
  - `headers` (dict): Headers for the request.
  - `retries` (int): Number of retries in case of failure.
  - `retry_delay` (int): Delay between retries.
- **Returns**: The fetched data as a dictionary.

#### `build_request_url(self, base_url, affiliation, from_date, to_date, n_element, sort_type, sort_ord, cursor, has_abstract)`
- **Description**: Builds the request URL for the Crossref API.
- **Parameters**: 
  - `base_url` (str): The base URL for the Crossref API.
  - `affiliation` (str): The affiliation to filter results by.
  - `from_date` (str): The starting date for the data fetch.
  - `to_date` (str): The ending date for the data fetch.
  - `n_element` (str): Number of elements to fetch.
  - `sort_type` (str): The type of sorting.
  - `sort_ord` (str): The order of sorting.
  - `cursor` (str): The cursor for pagination.
  - `has_abstract` (bool): Whether to filter by presence of abstract.
- **Returns**: The constructed URL as a string.

#### `process_items(self, data, from_date, to_date, affiliation)`
- **Description**: Processes the fetched data to filter relevant items.
- **Parameters**: 
  - `data` (dict): The fetched data.
  - `from_date` (str): The starting date for the data fetch.
  - `to_date` (str): The ending date for the data fetch.
  - `affiliation` (str): The affiliation to filter results by.
- **Returns**: A list of filtered items.

#### `acollect_yrange(self, session, from_date, to_date, n_element, sort_type, sort_ord, cursor, retries, retry_delay)`
- **Description**: Asynchronously collects data for a given year range.
- **Parameters**: 
  - `session` (aiohttp.ClientSession): The aiohttp session.
  - `from_date` (str): The starting date for the data fetch.
  - `to_date` (str): The ending date for the data fetch.
  - `n_element` (str): Number of elements to fetch.
  - `sort_type` (str): The type of sorting.
  - `sort_ord` (str): The order of sorting.
  - `cursor` (str): The cursor for pagination.
  - `retries` (int): Number of retries in case of failure.
  - `retry_delay` (int): Delay between retries.
- **Returns**: A list of collected items.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments
- Thanks to the contributors of the Selenium and BeautifulSoup libraries.
- Special thanks to the Crossref API team for providing access to their data.

