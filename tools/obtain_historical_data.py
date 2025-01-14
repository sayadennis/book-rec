import datetime
import logging
import os
import time
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load API key
load_dotenv()
NYT_API_KEY = os.getenv("NYT_API_KEY")
BOOKS_BASE_URL = os.getenv("BOOKS_BASE_URL")
ARTICLES_BASE_URL = os.getenv("ARTICLES_BASE_URL")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

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
]

if not NYT_API_KEY:
    raise ValueError("No API key found. Please set NYT_API_KEY in the .env file.")

if not GOOGLE_API_KEY:
    raise ValueError("No API key found. Please set GOOGLE_API_KEY in the .env file.")

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
    params = {"api-key": NYT_API_KEY}
    response = requests.get(endpoint, params=params, timeout=30)
    time.sleep(12)  # Sleep for 12 seconds between requests
    response.raise_for_status()
    data = response.json()
    data_df = pd.DataFrame.from_dict(data["results"]["books"])[KEEP_FEATURES]
    data_df["bestseller_date"] = date
    data_df["category"] = category
    return data_df


def fetch_and_process_data(
    date: str, category: str, total_requests: int
) -> Tuple[pd.DataFrame, int]:
    """
    Fetch and process data for a given date and category.
    """
    data_df = fetch_bestsellers(date, category)
    total_requests += 1
    logger.info("Fetched data for %s - %s (rows %d)", date, category, data_df.shape[0])
    return data_df, total_requests


# Custom function to get the first non-NaN value
def first_non_nan(series: pd.Series) -> pd.Series:
    return series.dropna().iloc[0] if not series.dropna().empty else np.nan


def fetch_google_book_info(isbn: str, api_key: str | None) -> Dict:
    """
    Fetch book information from Google Books API using the given ISBN.
    This is to get the detailed book description that NYT does not have.

    Args:
        isbn (str): The ISBN of the book to search for.
        api_key (str): Your Google Books API key.

    Returns:
        dict: dictionary containing the book details, or error if no info found.
    """
    # Construct the API URL
    url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}&key={api_key}"

    # Make the API request
    try:
        response = requests.get(url, timeout=10)  # Timeout set to 10 seconds
    except requests.exceptions.Timeout:
        return {"error": "Request timed out"}
    except requests.exceptions.RequestException as e:
        return {"error": f"An error occurred: {e}"}

    # Check if the request was successful
    if response.status_code == 200:
        data = response.json()
        # Check if books are found
        if "items" in data:  # pylint: disable=no-else-return
            book_info = {
                "ISBN": isbn,
                "Published Date": data["items"][0]["volumeInfo"].get(
                    "publishedDate", "N/A"
                ),
                "Description": data["items"][0]["volumeInfo"].get("description", "N/A"),
            }
            return book_info
        else:
            return {"error": f"No books found for ISBN {isbn}."}
    else:
        return {
            "error": f"Failed to fetch data. HTTP Status Code: {response.status_code}"
        }


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

    print(f"Total requests made: {total_requests}")

    all_data = pd.concat(all_dataframes, ignore_index=True)
    all_data["bestseller_date"] = pd.to_datetime(all_data["bestseller_date"])
    all_data["category"] = all_data["category"].map(
        {
            "Combined Print and E-Book Fiction": "Fiction",
            "Combined Print and E-Book Nonfiction": "Fiction",
            "Hardcover Fiction": "Fiction",
            "Hardcover Nonfiction": "Nonfiction",
            "Trade Fiction Paperback": "Fiction",
            "Paperback Nonfiction": "Nonfiction",
            "Advice How-To and Miscellaneous": "Advice How-To and Misc",
        }
    )

    # Group by `primary_isbn13` and aggregate
    agg_data = (
        all_data.groupby("primary_isbn13")
        .agg(
            best_rank=("rank", "min"),
            max_weeks_on_list=("weeks_on_list", "max"),
            publisher=("publisher", first_non_nan),
            category=("category", first_non_nan),
            description=("description", first_non_nan),
            title=("title", first_non_nan),
            author=(
                "author",
                first_non_nan,
            ),  # Assuming author is the same for the same book
            latest_bestseller_date=("bestseller_date", "max"),
        )
        .reset_index()
    )

    # Get book descriptions from Google Books API
    for i in agg_data.index:
        google_book_info = fetch_google_book_info(
            agg_data.loc[i, "primary_isbn13"], api_key=GOOGLE_API_KEY
        )
        if (
            "Description"
            in google_book_info.keys()  # pylint: disable=consider-iterating-dictionary
        ):
            agg_data.loc[i, "google_description"] = google_book_info["Description"]
            agg_data.loc[i, "publication_date"] = google_book_info["Published Date"]

    return agg_data


if __name__ == "__main__":
    # Get directories for data and params
    current_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(current_dir, ".."))
    data_dir = os.path.join(repo_root, "data", "raw")

    # Create raw data directory if it doesn't exist
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    # Get today's parameters
    acquisition_dates = pd.read_csv(f"{current_dir}/acquisition_dates.csv")
    today = datetime.datetime.today().strftime("%Y-%m-%d")

    params = acquisition_dates[acquisition_dates["acquisition_date"] == today]

    if params.shape[0] == 0:
        print("No match for acquisition date.")
    else:
        start_date = params["start_date"].item()
        end_date = params["end_date"].item()
        # Get data and save
        bestseller_df = gather_bestseller_data(CATEGORIES, start_date, end_date)
        bestseller_df.to_csv(f"{data_dir}/bestsellers-{start_date}-to-{end_date}.csv")
