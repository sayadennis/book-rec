import datetime
import logging
import os
import time
from typing import Dict, List, Tuple

import pandas as pd
import requests
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load API key
load_dotenv()
API_KEY = os.getenv("NYT_API_KEY")
BOOKS_BASE_URL = os.getenv("BOOKS_BASE_URL")
ARTICLES_BASE_URL = os.getenv("ARTICLES_BASE_URL")

CATEGORIES = [
    "Combined Print and E-Book Fiction",
    "Combined Print and E-Book Nonfiction",
    "Hardcover Fiction",
    "Hardcover Nonfiction",
    "Trade Fiction Paperback",
    "Paperback Nonfiction",
    "Advice How-To and Miscellaneous",
]

KEEP_FEATURES = [
    "rank",
    "weeks_on_list",
    "primary_isbn13",
    "publisher",
    "description",
    "title",
    "author",
    # 'rank_last_week',
    # 'book_review_link',
    # 'first_chapter_link',
    # 'sunday_review_link',
    # 'article_chapter_link',
]

if not API_KEY:
    raise ValueError("No API key found. Please set NYT_API_KEY in the .env file.")

if not BOOKS_BASE_URL:
    raise ValueError("No base URL found. Please set BOOKS_BASE_URL in the .env file.")

if not ARTICLES_BASE_URL:
    raise ValueError(
        "No article URL found. Please set ARTICLES_BASE_URL in the .env file."
    )


# Function to get all Sundays within a date range
def get_sundays(start_date: str, end_date: str) -> List[str]:
    start = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
    # Adjust to the first Sunday on or after the start date
    start += datetime.timedelta(days=(6 - start.weekday()) % 7)
    # Get dates
    dates = []
    current_date = start
    while current_date <= end:
        dates.append(current_date.strftime("%Y-%m-%d"))
        current_date += datetime.timedelta(days=7)
    return dates


# Function to fetch bestseller data for a given date and category
def fetch_bestsellers(date: str, category: str) -> pd.DataFrame:
    endpoint = f"{BOOKS_BASE_URL}/lists/{date}/{category}.json"
    params = {"api-key": API_KEY}
    response = requests.get(endpoint, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    data_df = pd.DataFrame.from_dict(data["results"]["books"])[KEEP_FEATURES]
    data_df["bestseller_date"] = date
    data_df["category"] = category
    return data_df


def get_book_review_url_by_isbn13(
    isbn13: str = "9780593597033",
) -> List[str]:
    """
    Get the set of review URLs by ISBN-13.
    If no review is present, return empty set.
    """
    endpoint = f"{BOOKS_BASE_URL}/reviews.json"
    params = {"isbn": isbn13, "api-key": API_KEY}
    urls = []
    try:
        response = requests.get(endpoint, params=params, timeout=30)
        response.raise_for_status()
        response_json = response.json()
        if "status" in response_json and response_json["status"] == "OK":
            if response_json.get("num_results", 0) > 0:
                for result in response_json["results"]:
                    urls.append(result.get("url", ""))
            else:
                logger.info("No results found for ISBN: %s", isbn13)
        else:
            logger.warning("Unexpected response format or error: %s", response_json)
    except requests.exceptions.RequestException as e:
        logger.error("Request failed: %s", e)
    # response = requests.get(endpoint, params=params, timeout=30)
    # response = response.json()
    # if (response["status"]=="OK") and (response["num_results"] > 0):
    #     for i in range(response["num_results"]):
    #         urls.append(response["results"][i]["url"])
    return list(set(urls))


def get_review_content_by_url(url: str) -> Dict[str, str]:
    """
    Get the content of a review article by its URL.
    Save the abstract, lead paragraph, and headline into a dictionary.
    """
    # Use the Articles API to fetch the article content
    endpoint = f"{ARTICLES_BASE_URL}/articlesearch.json"
    params = {"fq": f'web_url:("{url}")', "api-key": API_KEY}
    response = requests.get(endpoint, params=params, timeout=30)
    response_json = response.json()
    results = {}
    results["abstract"] = response_json["response"]["docs"][0]["abstract"]
    results["lead_paragraph"] = response_json["response"]["docs"][0]["lead_paragraph"]
    results["headline"] = response_json["response"]["docs"][0]["headline"]["main"]
    return results


def fetch_and_process_data(
    date: str, category: str, total_requests: int
) -> Tuple[pd.DataFrame, int]:
    """
    Fetch and process data for a given date and category.
    """
    data_df = fetch_bestsellers(date, category)
    data_df = update_review_contents(data_df)
    total_requests += 1
    logger.info("Fetched data for %s - %s (rows %d)", date, category, data_df.shape[0])
    time.sleep(12)  # Sleep for 12 seconds between requests
    return data_df, total_requests


def update_review_contents(data_df: pd.DataFrame) -> pd.DataFrame:
    """
    Update the DataFrame with review contents for each book.
    """
    for i in data_df.index:
        urls = get_book_review_url_by_isbn13(data_df.loc[i, "primary_isbn13"])
        if urls:
            url = urls[0]
            review_contents = get_review_content_by_url(url)
            for feature_name in ["abstract", "lead_paragraph", "headline"]:
                data_df.at[i, feature_name] = review_contents.get(feature_name, "")
    return data_df


# Main function to gather bestseller data for all categories and dates
def gather_bestseller_data(
    categories: List[str], start_date: str, end_date: str
) -> pd.DataFrame:
    sundays = get_sundays(start_date, end_date)
    all_dataframes: List[pd.DataFrame] = []
    total_requests = 0

    for date in sundays:
        for category in categories:
            if total_requests >= 500:
                logger.info("Reached the daily limit of 500 requests.")
                return pd.concat(all_dataframes, ignore_index=True)
            try:
                data_df, total_requests = fetch_and_process_data(
                    date, category, total_requests
                )
                all_dataframes.append(data_df)
            except requests.exceptions.HTTPError as e:
                logger.error(
                    "Error fetching data for %s and category %s: %s", date, category, e
                )

    return pd.concat(all_dataframes, ignore_index=True)


# Test getting ISBNs of all
bestseller_df = gather_bestseller_data(CATEGORIES, "2023-01-01", "2023-01-02")

current_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.abspath(os.path.join(current_dir, ".."))
data_dir = os.path.join(repo_root, "data", "raw")

bestseller_df.to_csv(f"{data_dir}/bestsellers_2023.csv")
