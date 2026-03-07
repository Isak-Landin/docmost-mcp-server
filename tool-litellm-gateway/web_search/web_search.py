import os
from duckduckgo_search import DDGS


WEB_SEARCH_MAX_RESULTS = int(os.getenv("WEB_SEARCH_MAX_RESULTS", "5"))


def web_search(query: str):
    with DDGS() as ddgs:
        return list(ddgs.text(query, max_results=WEB_SEARCH_MAX_RESULTS))