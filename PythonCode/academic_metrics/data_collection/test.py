from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
import json
from bs4 import BeautifulSoup
from openai import OpenAI
import os
import requests
from dotenv import load_dotenv

load_dotenv()
# Load your API key from an environment variable or directly set it here
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)
# Load the data from the JSON file
with open('fullData.json', 'r') as f:
    data = json.load(fp=f)
        
# Identify DOIs for entries that are missing abstracts
query_dict = {elem['DOI']: elem['URL'] for elem in data if elem.get('abstract', 'NA') == 'NA'}

# Get a subset of the first 20 items from query_dict
subset_query_dict = dict(list(query_dict.items())[:20])


output_dict = {}
for index, (doi, url) in enumerate(subset_query_dict.items()):
    # Set up the WebDriver (for Chrome, replace with the path to your downloaded ChromeDriver)
    service = Service('/home/usboot/Downloads/geckodriver')  # Update this path
    driver = webdriver.Firefox(service=service)

    try:
        driver.get(url)

        # Get the page content
        page_content = driver.page_source

        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(page_content, 'html.parser')
        body_content = str(soup.body)  # Extract the <body> element as a string

        # # Try to find the abstract using common patterns
        # abstract = None
        # abstract_div = soup.find('div', class_='abstract')
        # if abstract_div:
        #     abstract = abstract_div.get_text( strip=True)
        # else:
        #     abstract_tag = soup.find('abstract')
        #     if abstract_tag:
        #         abstract = abstract_tag.get_text(separator=' ', strip=True)

        # if not abstract:
        #     abstract = f"Abstract not found for DOI {doi}"

        
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an HTML processing assistant. Given a string of HTML from a DOI webpage, extract the full abstract for the academic research paper. The abstract is usually found within <abstract> tags, <div> tags with class 'abstract', or similar HTML elements. Please make sure to extract all abstract text until the next significant element."},
                {
                    "role": "user",
                    "content": body_content
                }
            ]
        )
        Abstract = completion.choices[0].message.content

        output_dict[doi] = Abstract

        with open(f"runs/outputData{index}.json", 'w') as f:
            json.dump(output_dict, f, indent=4)
    except TimeoutException as timeout_err:
        print(f"Timeout error occurred for DOI {doi}: {timeout_err}")
    except WebDriverException as web_driver_err:
        print(f"WebDriver error occurred for DOI {doi}: {web_driver_err}")
    except NoSuchElementException as no_elem_err:
        print(f"No such element error occurred for DOI {doi}: {no_elem_err}")
    except Exception as e:
        print(f"An error occurred for DOI {doi}: {e}")
    finally:
        # Close the browser
        driver.quit()

# Optionally, save the output_dict to a file
with open('test.json', 'w') as f:
    json.dump(output_dict, f, indent=4)