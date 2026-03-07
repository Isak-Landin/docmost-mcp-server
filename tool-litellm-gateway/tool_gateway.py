import json
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from duckduckgo_search import DDGS


ARCHON_BASE_URL = os.getenv("ARCHON_BASE_URL", "http://archon:3737")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "seamon67/Ministral-3-Reasoning:14b")

WEB_SEARCH_MAX_RESULTS = int(os.getenv("WEB_SEARCH_MAX_RESULTS", "5"))
MAX_TOOL_LOOPS = int(os.getenv("MAX_TOOL_LOOPS", "5"))

app = FastAPI()


class ChatRequest(BaseModel):
    message: str


def archon_search(query: str):
    r = requests.post(
        f"{ARCHON_BASE_URL}/api/knowledge-items/search",
        json={"query": query},
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


def archon_store(data: dict):
    r = requests.post(
        f"{ARCHON_BASE_URL}/api/documents/upload",
        json=data,
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


def archon_rag_query(data: dict):
    r = requests.post(
        f"{ARCHON_BASE_URL}/api/rag/query",
        json=data,
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


def web_search(query: str):
    with DDGS() as ddgs:
        return list(ddgs.text(query, max_results=WEB_SEARCH_MAX_RESULTS))


def run_tool(tool_name: str, arguments: dict):
    if tool_name == "archon_search":
        return archon_search(arguments.get("query", ""))

    if tool_name == "archon_store":
        return archon_store(arguments)

    if tool_name == "archon_rag_query":
        return archon_rag_query(arguments)

    if tool_name == "web_search":
        return web_search(arguments.get("query", ""))

    return {
        "error": "unknown_tool",
        "tool_name": tool_name,
        "arguments": arguments,
    }


def build_system_prompt() -> str:
    return """
You are an assistant with access to tools.

Available tools:
1. archon_search
   Arguments:
   {
     "query": "string"
   }

2. archon_store
   Arguments:
   {
     "project": "string",
     "note": "string"
   }

3. archon_rag_query
   Arguments:
   {
   }

4. web_search
   Arguments:
   {
     "query": "string"
   }

Rules:
- Always return valid JSON only.
- If you need a tool, respond exactly like this:
  {
    "action": "tool",
    "tool_name": "archon_search",
    "arguments": {
      "query": "example query"
    }
  }

- If you do not need a tool, respond exactly like this:
  {
    "action": "final",
    "answer": "your final answer here"
  }

- After a tool result is provided, either request another tool or return a final answer.
- Never output markdown.
- Never output explanations outside the JSON.
""".strip()


def call_ollama(messages: list[dict]):
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
    }

    r = requests.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        json=payload,
        timeout=120,
    )

    if not r.ok:
        print("OLLAMA STATUS:", r.status_code, flush=True)
        print("OLLAMA BODY:", r.text, flush=True)
        r.raise_for_status()

    data = r.json()
    return data["message"]["content"]


def parse_model_output(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {
            "action": "final",
            "answer": text,
        }


@app.get("/archon_search")
def http_archon_search(q: str):
    return archon_search(q)


@app.post("/archon_store")
def http_archon_store(data: dict):
    return archon_store(data)


@app.post("/archon_rag_query")
def http_archon_rag_query(data: dict):
    return archon_rag_query(data)


@app.get("/web_search")
def http_web_search(q: str):
    return web_search(q)


@app.post("/chat")
def chat(req: ChatRequest):
    messages = [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": req.message},
    ]

    for _ in range(MAX_TOOL_LOOPS):
        try:
            model_text = call_ollama(messages)
        except requests.RequestException as e:
            raise HTTPException(status_code=500, detail=f"ollama_request_failed: {str(e)}")

        parsed = parse_model_output(model_text)
        action = parsed.get("action")

        if action == "final":
            return {
                "ok": True,
                "answer": parsed.get("answer", ""),
                "messages": messages,
            }

        if action != "tool":
            return {
                "ok": False,
                "error": "invalid_model_action",
                "raw_output": model_text,
            }

        tool_name = parsed.get("tool_name", "")
        arguments = parsed.get("arguments", {})

        try:
            tool_result = run_tool(tool_name, arguments)
        except requests.RequestException as e:
            print(f"OLLAMA REQUEST FAILED: {e}", flush=True)
            raise HTTPException(status_code=500, detail=f"ollama_request_failed: {str(e)}")
        except Exception as e:
            tool_result = {
                "error": "tool_runtime_failed",
                "tool_name": tool_name,
                "message": str(e),
            }

        messages.append({"role": "assistant", "content": model_text})
        messages.append({
            "role": "user",
            "content": json.dumps(
                {
                    "tool_result_for": tool_name,
                    "tool_arguments": arguments,
                    "tool_output": tool_result,
                },
                ensure_ascii=False,
            ),
        })

    return {
        "ok": False,
        "error": "max_tool_loops_reached",
        "message": f"Model exceeded {MAX_TOOL_LOOPS} tool iterations",
    }