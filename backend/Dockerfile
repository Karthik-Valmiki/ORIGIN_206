FROM python:3.12-slim

WORKDIR /app

# System deps: OpenCV + Tesseract OCR (fast install, no PyTorch)
RUN apt-get update && apt-get install -y \
    libglib2.0-0 libsm6 libxext6 libxrender-dev libgl1 libgomp1 \
    tesseract-ocr tesseract-ocr-eng tesseract-ocr-hin \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps (separate layer = cached on code-only changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source (overridden by volume mount in dev)
COPY app/ ./app/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
