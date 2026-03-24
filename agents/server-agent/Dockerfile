FROM python:3.12-slim

# System deps: SNMP tools + MIB files
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsnmp-dev \
    snmp \
    snmp-mibs-downloader \
    && rm -rf /var/lib/apt/lists/*

# Download MIBs (needed for HOST-RESOURCES-MIB, IF-MIB)
RUN download-mibs 2>/dev/null || true

WORKDIR /app

# Install shared library first (better layer caching)
COPY shared/ /app/shared/
RUN pip install --no-cache-dir -e /app/shared/

# Install agent dependencies
COPY agents/server-agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agents/server-agent/src/ /app/src/

CMD ["python", "-m", "src.main"]
