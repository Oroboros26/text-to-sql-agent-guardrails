FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -e .
CMD ["python", "-m", "sql_agent", "Top 3 products by revenue?"]
