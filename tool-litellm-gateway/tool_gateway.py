import json
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import requests

from archon.archon import archon_search, archon_rag_query
from web_search.web_search import web_search
from ollama.ollama_client import call_ollama, parse_model_output


MAX_TOOL_LOOPS = int(os.getenv("MAX_TOOL_LOOPS", "5"))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://141.0.85.201:41988",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str


def run_tool(tool_name: str, arguments: dict):
    if tool_name == "archon_search":
        return archon_search(
            query=arguments.get("query", ""),
            source=arguments.get("source", ""),
            match_count=arguments.get("match_count", 5),
            return_mode=arguments.get("return_mode", "chunks"),
        )

    if tool_name == "archon_rag_query":
        return archon_rag_query(
            query=arguments.get("query", ""),
            source=arguments.get("source", ""),
            match_count=arguments.get("match_count", 5),
            return_mode=arguments.get("return_mode", "chunks"),
        )

    if tool_name == "web_search":
        return web_search(arguments.get("query", ""))

    return {
        "error": "unknown_tool",
        "tool_name": tool_name,
        "arguments": arguments,
    }


@app.get("/archon_search")
def http_archon_search(
    q: str,
    source: str = "",
    match_count: int = 5,
    return_mode: str = "chunks",
):
    return archon_search(
        query=q,
        source=source,
        match_count=match_count,
        return_mode=return_mode,
    )


@app.post("/archon_rag_query")
def http_archon_rag_query(data: dict):
    return archon_rag_query(
        query=data.get("query", ""),
        source=data.get("source", ""),
        match_count=data.get("match_count", 5),
        return_mode=data.get("return_mode", "chunks"),
    )


@app.get("/web_search")
def http_web_search(q: str):
    return web_search(q)


@app.post("/chat")
def chat(req: ChatRequest):
    history: list[dict] = []

    for _ in range(MAX_TOOL_LOOPS):
        try:
            ollama_data = call_ollama(
                user_message=req.message,
                history=history,
            )
        except requests.RequestException as e:
            raise HTTPException(status_code=500, detail=f"ollama_request_failed: {str(e)}")

        parsed = parse_model_output(ollama_data)

        if parsed.get("action") == "tool":
            tool_name = parsed.get("tool_name", "")
            arguments = parsed.get("arguments", {})

            try:
                tool_result = run_tool(tool_name, arguments)
            except requests.RequestException as e:
                print(f"REQUEST FAILED: {e}", flush=True)
                raise HTTPException(status_code=500, detail=f"tool_request_failed: {str(e)}")
            except Exception as e:
                tool_result = {
                    "error": "tool_runtime_failed",
                    "tool_name": tool_name,
                    "message": str(e),
                }

            assistant_message = ollama_data.get("message", {}) or {}
            history.append(assistant_message)
            history.append(
                {
                    "role": "tool",
                    "tool_name": tool_name,
                    "content": json.dumps(tool_result, ensure_ascii=False),
                }
            )
            continue

        return {
            "ok": True,
            "answer": parsed.get("answer", ""),
            "thinking": parsed.get("thinking", ""),
            "messages": history,
            "ollama_response": ollama_data,
        }

    return {
        "ok": False,
        "error": "max_tool_loops_reached",
        "message": f"Model exceeded {MAX_TOOL_LOOPS} tool iterations",
    }


@app.get("/debug")
def debug():
    return FileResponse("index.html")