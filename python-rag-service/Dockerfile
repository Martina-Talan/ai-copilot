FROM python:3.10-slim

# Install tesseract & system packages directly in final image
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-deu \
    libtesseract-dev \
    libleptonica-dev \
    poppler-utils \
    pkg-config \
    build-essential \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata

# Install Python deps
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel

RUN pip install --no-cache-dir -r requirements.txt \
    --extra-index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir "rapidfuzz>=3.7,<4"

# Copy app source code
COPY . .

ENV PATH=/usr/local/bin:$PATH

EXPOSE 8000

CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000","--log-level","debug"]
