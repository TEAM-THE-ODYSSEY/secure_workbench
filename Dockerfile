FROM python:3.12-slim

# System dependencies for PDF processing, PostgreSQL, and PaddleOCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# PaddlePaddle/PaddleOCR — disable MKLDNN to avoid PIR+OneDNN CPU crashes
ENV PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT=0
ENV PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True

WORKDIR /app

# Install Lightweight CPU PyTorch first
RUN pip install --no-cache-dir --default-timeout=1000 torch --index-url https://download.pytorch.org/whl/cpu

# Pin numpy < 2.0 for PaddlePaddle compatibility, then install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=1000 "numpy<2.0" && \
    pip install --no-cache-dir --default-timeout=1000 -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu



# Download spaCy model
RUN python -m spacy download en_core_web_sm || true

# Copy application code
COPY . .

# Expose API port
EXPOSE 8000

# Default: run FastAPI server
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]
