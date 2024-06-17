import datetime
import os
import time
from typing import Any, Dict, List, Set

import requests
from dotenv import load_dotenv

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

    dates = []
    current_date = start
    while current_date <= end:
        dates.append(current_date.strftime("%Y-%m-%d"))
        current_date += datetime.timedelta(days=7)

    return dates


# Function to fetch bestseller data for a given date and category
def fetch_bestsellers(date: str, category: str) -> List[Dict]:
    endpoint = f"{BOOKS_BASE_URL}/lists/{date}/{category}.json"
    params = {"api-key": API_KEY}
    response = requests.get(endpoint, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    return data["results"]["books"]


# Function to extract ISBN13s from the bestseller data
def extract_isbn13s(books: List[Dict]) -> Set[str]:
    isbn13s = {book["primary_isbn13"] for book in books if "primary_isbn13" in book}
    return isbn13s


# Main function to gather ISBN13s for all categories and dates
def gather_isbn13s(categories: List[str], start_date: str, end_date: str) -> Set[str]:
    sundays = get_sundays(start_date, end_date)
    all_isbn13s: set[str] = set()
    total_requests = 0
    for date in sundays:
        for category in categories:
            if total_requests >= 500:
                print("Reached the daily limit of 500 requests.")
                return all_isbn13s
            try:
                books = fetch_bestsellers(date, category)
                isbn13s = extract_isbn13s(books)
                all_isbn13s.update(isbn13s)
                total_requests += 1
                print(f"Fetched data for {date} - {category} (size {len(isbn13s)})")
                time.sleep(12)  # Sleep for 12 seconds between requests
            except requests.exceptions.HTTPError as e:
                print(f"Error fetching data for {date} and category {category}: {e}")
    return all_isbn13s


def get_book_reviews_by_isbn13(
    isbn13: str = "9780593597033",
) -> Dict[str, Any]:
    """
    Get book reviews by ISBN-13.
    """
    endpoint = f"{BOOKS_BASE_URL}/reviews.json"
    params = {"isbn": isbn13, "api-key": API_KEY}
    response = requests.get(endpoint, params=params, timeout=30)
    return response.json()


def get_article_content_by_url(url: str) -> Dict[str, Dict[str, Any]]:
    """
    Get the full content of an article by its URL.
    """
    # Use the Articles API to fetch the article content
    endpoint = f"{ARTICLES_BASE_URL}/articlesearch.json"
    params = {"fq": f'web_url:("{url}")', "api-key": API_KEY}
    response = requests.get(endpoint, params=params, timeout=30)
    return response.json()


# Test getting ISBNs of all
isbn13s_2023 = gather_isbn13s(CATEGORIES[:2], "2023-01-01", "2023-03-31")

with open("/home/srd6051/ISBN13_bestsellers_2023.txt", "w") as f:
    for item in isbn13s_2023:
        f.write(f"{item}\n")

# Test getting review article information for one book
print("\n\nTesting retrieval of a review article...")
results = get_book_reviews_by_isbn13()  # Get example review

# Check if there are results and extract the URL of the first review
num_results = results.get("num_results")
if isinstance(num_results, int) and num_results > 0:
    results_list = results.get("results", [])
    if isinstance(results_list, list) and len(results_list) > 0:
        review_url = results_list[0].get("url")
        print("Review URL:", review_url)
        # Fetch the full article content
        article_content = get_article_content_by_url(review_url)
        if article_content["status"] == "OK":
            docs = article_content["response"]["docs"]
            if docs:
                full_article = docs[0]
                print("Article Headline:", full_article["headline"]["main"])
                print("Article Lead Paragraph:", full_article["lead_paragraph"])
                print("Article Full Text:", full_article["snippet"])
                print("Rank:", full_article["keywords"][0]["rank"])
            else:
                print("No article content found.")
    else:
        print("Error fetching article content.")
else:
    print("No reviews found for this title.")
