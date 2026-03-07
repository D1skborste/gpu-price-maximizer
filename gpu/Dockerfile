FROM python:3.11-slim
WORKDIR /app
RUN pip install ollama duckduckgo-search requests beautifulsoup4
COPY search_agent.py .
CMD ["python", "search_agent.py"]