def get_tools() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": "archon_search",
                "description": (
                    "Search Archon's indexed knowledge items and return structured retrieval results. "
                    "Use this when you want relevant matches, chunks, or indexed knowledge entries "
                    "from the stored knowledge base."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query to run against Archon's indexed knowledge.",
                        },
                        "source": {
                            "type": "string",
                            "description": (
                                "Optional source filter. Use an empty string if no source filter is needed."
                            ),
                        },
                        "match_count": {
                            "type": "integer",
                            "description": "Number of matches to request from Archon.",
                            "default": 5,
                        },
                        "return_mode": {
                            "type": "string",
                            "description": (
                                "Return mode for Archon results. Use 'chunks' unless another mode is explicitly required."
                            ),
                            "default": "chunks",
                        },
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "archon_rag_query",
                "description": (
                    "Query Archon's RAG pipeline for an answer based on the stored knowledge base. "
                    "Use this when you want Archon to synthesize or answer from knowledge, "
                    "not just return raw retrieval matches."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The question or prompt to send to Archon's RAG query endpoint.",
                        },
                        "source": {
                            "type": "string",
                            "description": (
                                "Optional source filter. Use an empty string if no source filter is needed."
                            ),
                        },
                        "match_count": {
                            "type": "integer",
                            "description": "Number of retrieved matches Archon should use.",
                            "default": 5,
                        },
                        "return_mode": {
                            "type": "string",
                            "description": (
                                "Return mode for Archon results. Use 'chunks' unless another mode is explicitly required."
                            ),
                            "default": "chunks",
                        },
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": (
                    "Search the public web. Use this only when Archon is not the right source, "
                    "or when external and up-to-date public information is needed."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The web search query.",
                        },
                    },
                    "required": ["query"],
                },
            },
        },
    ]