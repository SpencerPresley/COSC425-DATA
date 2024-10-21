import time
import requests
import json
import os
import logging
import asyncio
import aiohttp
from tqdm.asyncio import tqdm

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("app.log")],
)
logger = logging.getLogger(__name__)

# Maximum number of concurrent requests allowed
MAX_CONCURRENT_REQUESTS = 2  # Limit to 2 concurrent tasks at a time

# Semaphore to control the rate of concurrent requests
semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)


async def fetch_data(session, url, headers, retries, retry_delay):
    num_iter = 0
    while num_iter < retries:
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 429:
                    retry_after = retry_delay
                    logger.debug(
                        f"Hit request limit, retrying in {retry_after} seconds..."
                    )
                    await asyncio.sleep(retry_after)
                    num_iter += 1
                    continue
                elif response.status == 200:
                    logging.info(f"Getting data from response...")
                    data = await response.json()
                    return data
                else:
                    logger.error(f"Unexpected status {response.status} for URL: {url}")
                    return None
        except aiohttp.ClientError as e:
            logger.error(f"Network error: {e}")
            return None
    logger.warning(f"Exceeded max retries for URL: {url}")
    return None


def build_request_url(
    base_url,
    affiliation,
    from_date,
    to_date,
    n_element,
    sort_type,
    sort_ord,
    cursor,
    has_abstract=False,
):
    ab_state = ""
    if has_abstract:
        ab_state = ",has-abstract:1"

    return f"{base_url}?query.affiliation={affiliation}&filter=from-pub-date:{from_date},until-pub-date:{to_date}{ab_state}&sort={sort_type}&order={sort_ord}&rows={n_element}&cursor={cursor}"


def process_items(data, from_date, to_date):
    filtered_data = []
    for item in data.get("items", []):
        if item["published"]["date-parts"][0][0] >= int(
            from_date.split("-")[0]
        ) and item["published"]["date-parts"][0][0] <= int(to_date.split("-")[0]):
            count = 0
            for author in item.get("author", []):
                for affil in author.get("affiliation", []):
                    if "salisbury univ" in affil.get("name", "").lower():
                        count += 1
            if count > 0:
                filtered_data.append(item)
    return filtered_data


async def Crf_dict_cursor_async(
    session: aiohttp.ClientSession,
    base_url: str = "https://api.crossref.org/works",
    affiliation: str = "Salisbury%20University",
    from_date: str = "2018-01-01",
    to_date: str = "2024-10-09",
    n_element: str = "1000",
    sort_type: str = "relevance",
    sort_ord: str = "desc",
    cursor: str = "*",
    retries: int = 5,
    retry_delay: int = 3,
):
    logger.info("Starting Crf_dict_cursor_async function")
    item_list = []
    processed_papers = 0
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Rommel Center",
        "mailto": "cbarbes1@gulls.salisbury.edu",
    }

    async with semaphore:
        req_url = build_request_url(
            base_url,
            affiliation,
            from_date,
            to_date,
            n_element,
            sort_type,
            sort_ord,
            cursor,
        )
        logger.debug(f"Request URL: {req_url}")

        data = await fetch_data(session, req_url, headers, retries, retry_delay)
        if data is None:
            return (None, None)

        data = data.get("message", {})
        if data == {}:
            logging.debug(f"No data to process")
            return (None, None)
        total_docs = data.get("total-results", 0)
        if total_docs == 0:
            logging.debug(f"No docs to process")
            return (None, None)
        logger.info(f"Processing API Pages from {from_date} to {to_date}")

        while processed_papers < total_docs:
            filtered_data = process_items(data, from_date, to_date)

            item_list.extend(filtered_data)
            processed_papers += len(filtered_data)

            cursor = data.get("next-cursor", None)
            if cursor is None:
                break

            req_url = build_request_url(
                base_url,
                affiliation,
                from_date,
                to_date,
                n_element,
                sort_type,
                sort_ord,
                cursor,
            )
            data = await fetch_data(session, req_url, headers, retries, retry_delay)
            if data is None:
                break

            data = data.get("message", {})
            if filtered_data == []:
                break
            await asyncio.sleep(3)

    logger.info("Processing Complete")
    return (item_list, cursor)


async def fetch_data_for_multiple_years(
    years: list = [2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024]
):
    async with aiohttp.ClientSession() as session:
        tasks = [
            Crf_dict_cursor_async(
                session, from_date=f"{year}-01-01", to_date=f"{year}-12-31"
            )
            for year in years
        ]

        start_time = time.time()
        results = await asyncio.gather(*tasks)

        final_result = []
        for result, _ in results:
            if result is not None:
                final_result.extend(result)

        end_time = time.time()
        logger.info(f"All data fetched. This took {end_time - start_time} seconds")

        return final_result


if __name__ == "__main__":
    result_list = asyncio.run(fetch_data_for_multiple_years())
    logger.info(f"Number of items: {len(result_list)}")
    with open("fullData.json", "w") as file:
        json.dump(result_list, fp=file, indent=4)
