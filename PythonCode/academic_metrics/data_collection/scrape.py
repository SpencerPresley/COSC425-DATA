import os
from dotenv import load_dotenv
from firecrawl import FirecrawlApp
import json
from openai import OpenAI
import requests

load_dotenv()

firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")
# Load your API key from an environment variable or directly set it here
api_key = os.getenv("OPENAI_API_KEY")


def firecrawl_missing_abstracts(url_dict: dict[str, str]):
    app = FirecrawlApp(api_key=firecrawl_api_key)

    client = OpenAI(api_key=api_key)
    output_dict = {}
    for doi, url in url_dict.items():
        # Crawl a website:
        scrape_status = app.scrape_url(url, params={"formats": ["markdown", "html"]})

        try:
            scrape_data = scrape_status["content"]

            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": " You are a markdown processing assistant. Given a string of markdown, the markdown are from doi webpages that have abstracts for academic research papers. You extract the abstract from the markdown and return it.",
                    },
                    {"role": "user", "content": scrape_data},
                ],
            )
            Abstract = completion.choices[0].message.content

            output_dict[doi] = Abstract
        except Exception as e:
            print(f"Ran out of tokens {e}")
            return output_dict
    return output_dict


def AI_get_missing_abstracts(url_dict: dict[str, str]):
    client = OpenAI(api_key=api_key)
    output_dict = {}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }

    for doi, url in url_dict.items():
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # Raise an exception for HTTP errors

            scrape_data = response.content.decode("utf-8")

            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": " You are a html processing assistant. Given a string of html, the html are from doi webpages that have abstracts for academic research papers. You extract the abstract from the html and return it.",
                    },
                    {"role": "user", "content": scrape_data},
                ],
            )
            Abstract = completion.choices[0].message.content

            output_dict[doi] = Abstract
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred for DOI {doi}: {http_err}")
        except requests.exceptions.RequestException as req_err:
            print(f"Request error occurred for DOI {doi}: {req_err}")
        except Exception as e:
            print(f"An error occurred for DOI {doi}: {e}")

    return output_dict
