FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 libpq-dev gcc curl \
    fonts-noto-cjk fonts-liberation \
    tesseract-ocr tesseract-ocr-chi-sim \
    poppler-utils \
    libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libxkbcommon0 \
    libatspi2.0-0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libdrm2 libpango-1.0-0 libcairo2 libasound2 libnspr4 libnss3 \
    && rm -rf /var/lib/apt/lists/*

# Playwright Chromium — no --with-deps (fonts installed manually above)
RUN pip install playwright==1.49.1 \
    && playwright install chromium

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
