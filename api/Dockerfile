FROM python:3.12-slim

WORKDIR /app

# Install shared library
COPY shared/ /app/shared/
RUN pip install --no-cache-dir -e /app/shared/

# Install API dependencies
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/src/ /app/src/

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
