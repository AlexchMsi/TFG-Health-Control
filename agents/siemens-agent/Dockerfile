FROM python:3.12-slim

WORKDIR /app

# Copy and install shared library first (better layer caching)
COPY shared/ /app/shared/
RUN pip install --no-cache-dir -e /app/shared/

# Install agent dependencies
COPY agents/siemens-agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent source
COPY agents/siemens-agent/src/ /app/src/

CMD ["python", "-m", "src.main"]
