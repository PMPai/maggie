FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 libpq-dev gcc curl \
    && rm -rf /var/lib/apt/lists/*

# Playwright Chromium install disabled — Playwright 1.49 fails on newer Debian
# (ttf-unifont / ttf-ubuntu-font-family packages no longer available).
# Re-enable when upgrading Playwright to a version that supports Debian 12+.
# RUN pip install playwright==1.49.1 \
#     && playwright install --with-deps chromium

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
