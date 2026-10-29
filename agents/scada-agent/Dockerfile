FROM python:3.12-slim

WORKDIR /app

COPY shared/ /app/shared/
RUN pip install --no-cache-dir -e /app/shared/

COPY agents/scada-agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agents/scada-agent/src/ /app/src/

CMD ["python", "-m", "src.main"]
