FROM python:3.12-slim

WORKDIR /app

COPY shared/ /app/shared/
RUN pip install --no-cache-dir -e /app/shared/

COPY agents/recommendation-agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agents/recommendation-agent/src/ /app/src/

CMD ["python", "-m", "src.main"]
