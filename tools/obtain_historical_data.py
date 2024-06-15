import os
from typing import Any, Dict, List, Union

import requests
from dotenv import load_dotenv

# Load API key
load_dotenv()
API_KEY = os.getenv("NYT_API_KEY")
BOOKS_BASE_URL = os.getenv("BOOKS_BASE_URL")
ARTICLES_BASE_URL = os.getenv("ARTICLES_BASE_URL")

if not API_KEY:
    raise ValueError("No API key found. Please set NYT_API_KEY in the .env file.")

if not BOOKS_BASE_URL:
    raise ValueError("No base URL found. Please set BOOKS_BASE_URL in the .env file.")

if not ARTICLES_BASE_URL:
    raise ValueError(
        "No article URL found. Please set ARTICLES_BASE_URL in the .env file."
    )


def get_bestsellers_by_date(
    published_date: str = "2023-08-08",
    top_five: bool = True,
) -> Dict[str, Any]:
    """
    Get the list of bestsellers by published date.
    """
    if top_five:
        endpoint = f"{BOOKS_BASE_URL}/lists/overview.json"
    else:
        endpoint = f"{BOOKS_BASE_URL}/lists/full-overview.json"
    params = {"published_date": published_date, "api-key": API_KEY}
    response = requests.get(endpoint, params=params, timeout=30)
    return response.json()


def filter_results_by_listname(
    response_json: Dict[str, Any],
    list_names: List[str] = [
        "Combined Print and E-Book Fiction",
        "Combined Print and E-Book Nonfiction",
        "Hardcover Fiction",
        "Hardcover Nonfiction",
        "Trade Fiction Paperback",
        "Paperback Nonfiction",
        "Advice How-To and Miscellaneous",
    ],
) -> Union[Dict[str, Dict[str, Any]], None]:
    if len(list_names) > 0:
        results = {
            x["list_name"]: x
            for x in response_json["results"]["lists"]
            if x["list_name"] in list_names
        }
    else:
        print("No list names specified. Returning empty list.")
        results = None
    return results


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


# Test getting review article information for one book

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
