FROM python:3.12-slim

WORKDIR /app

# Install shared library first (better layer caching)
COPY shared/ /app/shared/
RUN pip install --no-cache-dir -e /app/shared/

# Install agent dependencies
COPY agents/server-agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agents/server-agent/src/ /app/src/

CMD ["python", "-m", "src.main"]
