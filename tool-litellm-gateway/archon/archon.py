import os
import requests


ARCHON_BASE_URL = os.getenv("ARCHON_BASE_URL", "http://archon:8181")


def archon_search(
    query: str,
    source: str = "",
    match_count: int = 5,
    return_mode: str = "chunks",
):
    payload = {
        "query": query,
        "source": source,
        "match_count": match_count,
        "return_mode": return_mode,
    }

    r = requests.post(
        f"{ARCHON_BASE_URL}/api/knowledge-items/search",
        json=payload,
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


def archon_rag_query(
    query: str,
    source: str = "",
    match_count: int = 5,
    return_mode: str = "chunks",
):
    payload = {
        "query": query,
        "source": source,
        "match_count": match_count,
        "return_mode": return_mode,
    }

    r = requests.post(
        f"{ARCHON_BASE_URL}/api/rag/query",
        json=payload,
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


def archon_store(
    file_path: str,
    tags: str = "",
    knowledge_type: str = "technical",
    extract_code_examples: bool = True,
):
    with open(file_path, "rb") as f:
        files = {
            "file": (os.path.basename(file_path), f),
        }
        data = {
            "tags": tags,
            "knowledge_type": knowledge_type,
            "extract_code_examples": str(extract_code_examples).lower(),
        }

        r = requests.post(
            f"{ARCHON_BASE_URL}/api/documents/upload",
            files=files,
            data=data,
            timeout=120,
        )

    r.raise_for_status()
    return r.json()