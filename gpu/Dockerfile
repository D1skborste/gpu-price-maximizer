FROM python:3.11-slim
WORKDIR /app
RUN pip install ollama ddgs requests beautifulsoup4
COPY oracle_test.py .
CMD ["python", "oracle_test.py"]