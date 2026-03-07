FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir fastapi uvicorn requests duckduckgo-search

COPY tool_gateway.py /app/tool_gateway.py
COPY ollama /app/ollama
COPY archon /app/archon
COPY web_search /app/web_search

ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "tool_gateway:app", "--host", "0.0.0.0", "--port", "4100"]