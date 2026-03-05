from fastapi import FastAPI
import requests
from duckduckgo_search import DDGS

ARCHON_URL = "http://host.docker.internal:3737"

app = FastAPI()

@app.get("/archon_search")
def archon_search(q: str):
    r = requests.get(f"{ARCHON_URL}/search", params={"query": q}, timeout=20)
    return r.json()

@app.post("/archon_store")
def archon_store(data: dict):
    r = requests.post(f"{ARCHON_URL}/store", json=data, timeout=20)
    return r.json()

@app.get("/web_search")
def web_search(q: str):
    with DDGS() as ddgs:
        return list(ddgs.text(q, max_results=5))
